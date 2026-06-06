from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import pickle
import base64
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging
from lighthouse.config import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.send']


class GmailClient:
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API using OAuth2."""
        if os.path.exists(settings.gmail_token_path):
            with open(settings.gmail_token_path, 'rb') as token:
                self.creds = pickle.load(token)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    settings.gmail_credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(settings.gmail_token_path, 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.service = build('gmail', 'v1', credentials=self.creds)
    
    def get_unread_emails(
        self,
        since: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Fetch unread emails from the support inbox."""
        try:
            # Build query
            query = "is:unread"
            if since:
                date_str = since.strftime('%Y/%m/%d')
                query += f" after:{date_str}"
            
            # Search messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            
            # Fetch full message details
            emails = []
            for msg in messages:
                email = self._get_message_detail(msg['id'])
                if email:
                    emails.append(email)
            
            return emails
        except HttpError as error:
            logger.error(f"Error fetching emails: {error}")
            return []
    
    def _get_message_detail(self, message_id: str) -> Optional[Dict]:
        """Get full details of a message."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {}
            for header in message['payload'].get('headers', []):
                headers[header['name']] = header['value']
            
            # Extract body
            body = self._extract_body(message['payload'])
            
            return {
                'id': message_id,
                'thread_id': message.get('threadId'),
                'from': headers.get('From'),
                'to': headers.get('To'),
                'subject': headers.get('Subject'),
                'date': headers.get('Date'),
                'body': body,
                'snippet': message.get('snippet', '')
            }
        except HttpError as error:
            logger.error(f"Error fetching message detail: {error}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data', '')
                    body += self._decode_base64(data)
                elif 'parts' in part:
                    body += self._extract_body(part)
        else:
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data', '')
                body = self._decode_base64(data)
        
        return body
    
    def _decode_base64(self, data: str) -> str:
        """Decode base64 encoded data."""
        import base64
        return base64.urlsafe_b64decode(data).decode('utf-8')
    
    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: Optional[str] = None
    ) -> Optional[str]:
        """Send an email."""
        try:
            message = {
                'raw': base64.urlsafe_b64encode(
                    f"From: {settings.gmail_support_email}\n"
                    f"To: {to}\n"
                    f"Subject: {subject}\n\n"
                    f"{body}".encode('utf-8')
                ).decode('utf-8')
            }
            
            if thread_id:
                message['threadId'] = thread_id
            
            result = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            return result['id']
        except HttpError as error:
            logger.error(f"Error sending email: {error}")
            return None
    
    def mark_as_read(self, message_id: str) -> bool:
        """Mark a message as read."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"Error marking message as read: {error}")
            return False
    
    def mark_as_unread(self, message_id: str) -> bool:
        """Mark a message as unread."""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            return True
        except HttpError as error:
            logger.error(f"Error marking message as unread: {error}")
            return False
