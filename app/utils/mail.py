import os
import smtplib
from datetime import datetime
from sqlalchemy.orm import Session
from typing import Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from geoalchemy2.shape import to_shape
from app.models.schema import Customer, Barber, Booking
from app.core.config import settings

get_settings = settings()

def send_template_mail(to: str, subject: str, title: str, greeting: str, body_html: str, footer_note: str = ""):
    sender_email = get_settings.APP_MAIL
    password = get_settings.APP_PASSWORD
    
    if not sender_email or not password:
        return

    msg = MIMEMultipart('alternative')
    msg['From'] = f"thebarberdotcom <{sender_email}>"
    msg['To'] = to
    msg['Subject'] = subject

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            @media only screen and (max-width: 600px) {{
                .container {{ width: 100% !important; border-radius: 0 !important; }}
                .content {{ padding: 24px !important; }}
                .btn-col {{ display: block !important; width: 100% !important; margin-bottom: 12px !important; }}
            }}
        </style>
    </head>
    <body style="margin:0;padding:0;background-color:#f8fafc;font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;-webkit-font-smoothing:antialiased;">
        <table width="100%" border="0" cellpadding="0" cellspacing="0" style="background-color:#f8fafc;">
            <tr>
                <td align="center" style="padding: 40px 16px;">
                    <table class="container" width="600" border="0" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border:1px solid #e2e8f0;border-radius:16px;box-shadow:0 4px 6px -1px rgba(0,0,0,0.05);">
                        <tr>
                            <td style="padding: 32px 48px 0 48px;">
                                <div style="font-size:14px;font-weight:800;color:#0f172a;letter-spacing:2px;text-transform:uppercase;">
                                    THEBARBER<span style="color:#3b82f6;font-weight:400;text-transform:lowercase;">dot</span>COM
                                </div>
                            </td>
                        </tr>
                        <tr>
                            <td class="content" style="padding: 32px 48px 48px 48px;">
                                <h1 style="margin:0 0 12px;font-size:24px;font-weight:700;color:#0f172a;letter-spacing:-0.025em;">{title}</h1>
                                <p style="margin:0 0 32px;font-size:16px;line-height:1.6;color:#475569;">{greeting}</p>
                                
                                {body_html}

                                {f'<p style="margin-top:32px;font-size:13px;line-height:1.5;color:#94a3b8;">{footer_note}</p>' if footer_note else ""}
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 32px;background-color:#f1f5f9;border-top:1px solid #e2e8f0;text-align:center;border-bottom-left-radius:16px;border-bottom-right-radius:16px;">
                                <p style="margin:0;font-size:12px;color:#64748b;font-weight:500;letter-spacing:0.05em;">
                                    © 2026 THEBARBERDOTCOM SERVICES. ALL RIGHTS RESERVED.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, to, msg.as_string())
    except Exception as e:
        print(f"SMTP Error: {e}")

def booking_info_block(slot: datetime, barber: Any, service: str, price: str, seat_number: int, show_buttons: bool = True):
    formatted_time = slot.strftime("%A, %B %d • %I:%M %p")
    
    map_url = "https://maps.google.com"
    try:
        if barber.location:
            point = to_shape(barber.location)
            map_url = f"https://www.google.com/maps/search/?api=1&query={point.y},{point.x}"
    except: pass
    
    buttons_html = ""
    if show_buttons:
        buttons_html = f"""
        <tr>
            <td style="padding-top:24px;">
                <table width="100%" border="0" cellpadding="0" cellspacing="0">
                    <tr>
                        <td class="btn-col" width="48%">
                            <a href="{map_url}" target="_blank" style="display:block;background-color:#0f172a;color:#ffffff;text-align:center;padding:14px;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">Open in Maps</a>
                        </td>
                        <td class="spacer" width="4%"></td>
                        <td class="btn-col" width="48%">
                            <a href="tel:{barber.phone_number}" style="display:block;background-color:#ffffff;color:#0f172a;border:1px solid #e2e8f0;text-align:center;padding:14px;text-decoration:none;border-radius:8px;font-size:14px;font-weight:600;">Call Shop</a>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """

    return f"""
    <div style="background-color:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">
        <table width="100%" border="0" cellpadding="0" cellspacing="0">
            <tr>
                <td style="padding-bottom:20px;border-bottom:1px solid #f1f5f9;">
                    <div style="font-size:11px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:8px;">Appointment Details</div>
                    <div style="font-size:18px;color:#0f172a;font-weight:700;">{formatted_time}</div>
                </td>
            </tr>
            <tr>
                <td style="padding:20px 0;border-bottom:1px solid #f1f5f9;">
                    <div style="font-size:14px;color:#0f172a;font-weight:600;margin-bottom:4px;">{barber.shop_name}</div>
                    <div style="font-size:14px;color:#64748b;line-height:1.4;">{barber.address}</div>
                </td>
            </tr>
            <tr>
                <td style="padding-top:20px;">
                    <table width="100%" border="0" cellpadding="0" cellspacing="0">
                        <tr>
                            <td>
                                <div style="font-size:14px;color:#475569;">{service} (Seat : {seat_number})</div>
                            </td>
                            <td align="right">
                                <div style="font-size:16px;color:#0f172a;font-weight:700;">₹{price}</div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
            {buttons_html}
        </table>
    </div>
    """

def send_booking_confirmation_mail(booking_id: str, db: Session):
    print("3")
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not (b := booking): return
    cust = db.query(Customer).filter(Customer.id == b.customer_id).first()
    barb = db.query(Barber).filter(Barber.id == b.barber_id).first()
    if not (cust and barb): return
    
    content = booking_info_block(b.slot, barb, b.service, b.price, b.seat_number, show_buttons=True)
    send_template_mail(cust.email, "Booking Confirmed", "Your seat is reserved.", f"Hi {cust.name}, your appointment at {barb.shop_name} is confirmed. We've booked seat number {b.seat_number} for you.", content)

def send_booking_cancellation_mail(booking_id: str, db: Session):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not (b := booking): return
    cust = db.query(Customer).filter(Customer.id == b.customer_id).first()
    barb = db.query(Barber).filter(Barber.id == b.barber_id).first()
    
    content = booking_info_block(b.slot, barb, b.service, b.price, b.seat_number, show_buttons=False)
    send_template_mail(cust.email, "Booking Cancelled", "Appointment Cancelled", f"Hello {cust.name}, your reservation has been successfully cancelled. The following session is now available for others:", content)

def send_booking_cancellation_with_penalty_mail(booking_id: str, db: Session):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not (b := booking): return
    cust = db.query(Customer).filter(Customer.id == b.customer_id).first()
    barb = db.query(Barber).filter(Barber.id == b.barber_id).first()
    
    fine = "{:.2f}".format(float(b.price) * 0.2)
    penalty_html = f"""
    <div style="margin-top:20px;padding:16px;background-color:#fff1f2;border:1px solid #fda4af;border-radius:8px;text-align:center;">
        <div style="font-size:12px;color:#991b1b;font-weight:700;text-transform:uppercase;margin-bottom:4px;">Policy Notice</div>
        <div style="font-size:15px;color:#be123c;font-weight:700;">Late Cancellation Fee: ₹{fine}</div>
    </div>
    """
    content = booking_info_block(b.slot, barb, b.service, b.price, b.seat_number, show_buttons=False) + penalty_html
    send_template_mail(cust.email, "Cancellation Penalty Applied", "Important: Cancellation Fee", f"Hi {cust.name}, as this cancellation occurred within our 2-hour window, a penalty has been added to your account per our shop policy.", content)

def send_booking_reminder_mail(booking_id: str, minutes_before: int, db: Session):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not (b := booking): return
    cust = db.query(Customer).filter(Customer.id == b.customer_id).first()
    barb = db.query(Barber).filter(Barber.id == b.barber_id).first()
    
    content = booking_info_block(b.slot, barb, b.service, b.price, b.seat_number, show_buttons=True)
    send_template_mail(cust.email, "Reminder: Appointment Soon", "See you shortly!", f"Hi {cust.name}, just a friendly reminder that your session at {barb.shop_name} starts in {minutes_before} minutes.", content)