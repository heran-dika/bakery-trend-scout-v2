import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv
import unicodedata

load_dotenv()

def detect_language(text: str) -> str:
    """Detect language dari character range."""
    korean_count = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
    japanese_count = sum(1 for c in text if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
    arabic_count = sum(1 for c in text if '\u0600' <= c <= '\u06ff')
    chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    
    if korean_count > len(text) * 0.3:
        return "KO"
    elif japanese_count > len(text) * 0.3:
        return "JP"
    elif arabic_count > len(text) * 0.3:
        return "AR"
    elif chinese_count > len(text) * 0.3:
        return "ZH"
    else:
        return "EN"

def tag_trend_name(name: str) -> str:
    """Tag trend name dengan kode bahasa."""
    lang = detect_language(name)
    if lang != "EN":
        return f"[{lang}] {name}"
    return name

def generate_report() -> str:
    """Generate laporan HTML dari trend hari ini."""
    conn = sqlite3.connect("trends.db")
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    cursor.execute("""
        SELECT dt.id, dt.trend_name, dt.mention_count, dt.status, dt.sentiment, dt.trend_origin
        FROM daily_trends dt
        WHERE dt.date = ?
        ORDER BY dt.mention_count DESC
    """, (today,))
    
    trends = cursor.fetchall()
    
    domestic_trends = [t for t in trends if t[5] == "Domestic"]
    global_trends = [t for t in trends if t[5] == "Global"]
    
    html = '''
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            h2 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; }
            .trend-item { margin: 15px 0; padding: 10px; background: #f9f9f9; border-left: 4px solid #3498db; }
            .status { font-weight: bold; padding: 3px 6px; border-radius: 3px; }
            .status-baru { background: #e8f4f8; color: #0277bd; }
            .status-naik { background: #e8f5e9; color: #388e3c; }
            .status-stabil { background: #fff3e0; color: #f57c00; }
            .status-turun { background: #ffebee; color: #c62828; }
            .sources { font-size: 0.9em; color: #666; margin-top: 5px; }
            .radar { background: #fff8dc; padding: 10px; border-left: 4px solid #ff6b6b; margin-top: 20px; }
        </style>
    </head>
    <body>
    '''
    
    html += f"<h1>🍞 BakeryTrendScout — Daily Report</h1>"
    html += f"<p><strong>Date:</strong> {today.strftime('%A, %d %B %Y')}</p>"
    
    if domestic_trends:
        html += "<h2>📊 ID Pulse — Domestic Trends</h2>"
        for trend in domestic_trends:
            trend_id, name, mention_count, status, sentiment, _ = trend
            tagged_name = tag_trend_name(name)
            
            status_class = f"status-{status.lower()}"
            html += f'''
            <div class="trend-item">
                <strong>{tagged_name}</strong> 
                <span class="status {status_class}">{status}</span>
                <br>
                <small>Mentions: {mention_count} | Sentiment: {sentiment}</small>
            '''
            
            cursor.execute("""
                SELECT url, title FROM trend_sources 
                WHERE trend_id = ? 
                LIMIT 3
            """, (trend_id,))
            
            sources = cursor.fetchall()
            if sources:
                html += '<div class="sources">Sources: '
                source_links = [f'<a href="{src[0]}">{src[1][:50]}</a>' for src in sources]
                html += " | ".join(source_links)
                html += '</div>'
            
            html += "</div>"
    else:
        html += "<p><em>No domestic trends detected today.</em></p>"
    
    if global_trends:
        html += '<div class="radar"><h2>🌍 🔔 Radar Global</h2>'
        for trend in global_trends:
            trend_id, name, mention_count, status, sentiment, _ = trend
            tagged_name = tag_trend_name(name)
            
            html += f'''
            <div class="trend-item">
                <strong>{tagged_name}</strong> 
                <span class="status status-naik">Global</span>
                <br>
                <small>Mentions: {mention_count} | Sentiment: {sentiment}</small>
            '''
            
            cursor.execute("""
                SELECT url, title FROM trend_sources 
                WHERE trend_id = ? 
                LIMIT 3
            """, (trend_id,))
            
            sources = cursor.fetchall()
            if sources:
                html += '<div class="sources">Sources: '
                source_links = [f'<a href="{src[0]}">{src[1][:50]}</a>' for src in sources]
                html += " | ".join(source_links)
                html += '</div>'
            
            html += "</div>"
        
        html += "</div>"
    
    html += '''
    <hr>
    <p><small>Report generated by BakeryTrendScout AI | Language codes: [KO]=Korean, [JP]=Japanese, [AR]=Arabic, [ZH]=Chinese</small></p>
    </body>
    </html>
    '''
    
    conn.close()
    return html

def send_email(recipient: str, subject: str, html_body: str):
    """Kirim email via Gmail SMTP."""
    email_from = os.getenv("EMAIL_FROM")
    email_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    
    try:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = email_from
        message["To"] = recipient
        
        part = MIMEText(html_body, "html", "utf-8")
        message.attach(part)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(email_from, email_password)
            server.sendmail(email_from, recipient, message.as_string())
        
        print(f"✓ Email sent to {recipient}")
    
    except Exception as e:
        print(f"✗ Failed to send email: {e}")
