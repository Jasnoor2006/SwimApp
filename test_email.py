import smtplib

EMAIL_ADDRESS = 'jasnoor.tgs@gmail.com'
EMAIL_PASSWORD = 'iplemzczigjldln'  # <- REPLACE THIS with actual Gmail App Password (no spaces)

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    print("✅ Login successful!")