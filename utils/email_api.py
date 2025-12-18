import time
import imaplib
import email
import re
from email.header import decode_header


class RamblerIMAPEmail:
    def __init__(self, email_address, password):
        self.email_address = email_address
        self.password = password
        self.imap_server = 'imap.rambler.ru'
        self.imap_port = 993
        
    def connect(self):
        """Connect to Rambler IMAP server"""
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.email_address, self.password)
            return mail
        except Exception as e:
            print(f"Failed to connect to IMAP: {e}")
            return None
    
    def get_verification_code(self, timeout=60, check_interval=5):
        """
        Wait for and retrieve TikTok verification code from email
        
        Args:
            timeout: Maximum time to wait for email (seconds)
            check_interval: How often to check for new emails (seconds)
            
        Returns:
            Verification code string or None if not found
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                mail = self.connect()
                if not mail:
                    time.sleep(check_interval)
                    continue
                
                mail.select('INBOX')
                
                status, messages = mail.search(None, 'UNSEEN')
                
                if status == 'OK' and messages[0]:
                    email_ids = messages[0].split()
                    
                    for email_id in reversed(email_ids):
                        try:
                            status, msg_data = mail.fetch(email_id, '(RFC822)')
                            
                            if status != 'OK':
                                continue
                            
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)
                            
                            subject = self._decode_subject(msg.get('Subject', ''))
                            sender = msg.get('From', '')
                            
                            if 'tiktok' in sender.lower() or 'tiktok' in subject.lower():
                                
                                code = self._extract_code_from_email(msg)
                                
                                if code:
                                    mail.close()
                                    mail.logout()
                                    return code
                        
                        except Exception as e:
                            print(f"Error processing email: {e}")
                            continue
                
                mail.close()
                mail.logout()
                
            except Exception as e:
                print(f"Error checking emails: {e}")
            
            time.sleep(check_interval)
        
        return None
    
    def _decode_subject(self, subject):
        """Decode email subject"""
        if not subject:
            return ""
        
        decoded_parts = decode_header(subject)
        decoded_subject = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_subject += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_subject += part
        
        return decoded_subject
    
    def _extract_code_from_email(self, msg):
        """Extract verification code from email body"""
        body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        try:
                            body += part.get_payload(decode=True).decode('latin-1', errors='ignore')
                        except:
                            pass
                elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                    try:
                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        try:
                            body += part.get_payload(decode=True).decode('latin-1', errors='ignore')
                        except:
                            pass
        else:
            try:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            except:
                try:
                    body = msg.get_payload(decode=True).decode('latin-1', errors='ignore')
                except:
                    pass
        
        patterns = [
            r'\b(\d{4,8})\b',
            r'code[:\s]+(\d{4,8})',
            r'verification[:\s]+(\d{4,8})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
