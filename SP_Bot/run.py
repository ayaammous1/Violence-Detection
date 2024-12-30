from flask import Flask, Response, render_template_string
import cv2
import smtplib
from email.mime.text import MIMEText
from model import Model

app = Flask(__name__)

# Email Configuration
SENDER_EMAIL = "."
SENDER_PASSWORD = ""
RECIPIENT_EMAIL = ""
SMTP_SERVER = "smtp.office365.com"
SMTP_PORT = 587

model = Model()

CAMERA_FEED_URL = "http://192.168.10.200:4747/video"

violence_detected = False

email_sent = False

def send_email():
    """
    Sends an email notification when violence is detected.
    """
    global email_sent
    if email_sent:
        return

    try:
        subject = "Violence Detected Alert"
        body = "Violence has been detected in the live CCTV feed. Please take immediate action."
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
            print("Email sent successfully!")
        email_sent = True  # Set the flag to avoid duplicate emails
    except Exception as e:
        print(f"Failed to send email: {e}")

def generate_frames():
    """
    Capture frames from the camera feed and process them for violence detection.
    """
    global violence_detected, email_sent
    cap = cv2.VideoCapture(CAMERA_FEED_URL)

    while True:
        success, frame = cap.read()
        if not success:
            break

        label = model.predict(image=frame)['label']
        violence_detected = (label.lower() == "violence")

        if violence_detected:
            cv2.putText(frame, "VIOLENCE DETECTED!", (10, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2, cv2.LINE_AA)
            send_email()
        else:
            email_sent = False

        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

    cap.release()

@app.route('/')
def index():
    """
    Render the main page with the live stream and an alert message if violence is detected.
    """
    return render_template_string('''
    <!doctype html>
    <html lang="en">
    <head>
        <title>Live CCTV Feed</title>
        <style>
            body { font-family: Arial, sans-serif; text-align: center; background-color: #f4f4f9; color: #333; }
            h1 { margin: 20px; }
            .alert { color: red; font-size: 24px; font-weight: bold; margin-top: 20px; }
            video { width: 80%; height: auto; margin: auto; display: block; }
        </style>
        <script>
            async function checkViolence() {
                while (true) {
                    const response = await fetch('/violence_status');
                    const data = await response.json();
                    const alertBox = document.getElementById('alert-box');
                    if (data.violence) {
                        alertBox.textContent = 'VIOLENCE DETECTED!';
                    } else {
                        alertBox.textContent = '';
                    }
                    await new Promise(r => setTimeout(r, 1000));  // Check every second
                }
            }
            document.addEventListener('DOMContentLoaded', checkViolence);
        </script>
    </head>
    <body>
        <h1>Live CCTV Feed</h1>
        <img src="/video_feed" alt="Live Video Feed">
        <div id="alert-box" class="alert"></div>
        <footer>&copy; 2024 Live CCTV Surveillance</footer>
    </body>
    </html>
    ''')

@app.route('/video_feed')
def video_feed():
    """
    Route to serve the video feed.
    """
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/violence_status')
def violence_status():
    """
    API endpoint to return the current violence status.
    """
    return {"violence": violence_detected}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
