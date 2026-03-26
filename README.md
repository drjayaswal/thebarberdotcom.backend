---
title: thebarberdotcom
emoji: 💈
colorFrom: purple
colorTo: yellow
sdk: docker
app_port: 7860
---

# thebarberdotcom

Management system for barbershops featuring location-based search, seat management, and IST-compliant booking logic.

## Deployment

1. Create a **New Space** on Hugging Face Space.
2. Select **Docker** as the SDK.
3. Choose the **Blank** template.
4. Set the following **Secrets** in your Space Settings:
   - `DATABASE_URL`: Your Neon PostgreSQL connection string.
   - `APP_MAIL`: Your notification email.
   - `APP_PASSWORD`: Gmail App Password.
   - `JWT_SECRET`: Your authentication secret.

## Local Setup

```bash
pip install -r requirements.txt
python main.py