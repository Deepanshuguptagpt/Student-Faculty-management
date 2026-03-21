import ssl
import smtplib
from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend

class UnverifiedEmailBackend(DjangoEmailBackend):
    def open(self):
        if self.connection:
            return False
            
        try:
            # Create an unverified context
            context = ssl._create_unverified_context()
            
            # Create the connection
            self.connection = self.connection_class(
                self.host, self.port, timeout=self.timeout
            )
            
            # Handle STARTTLS
            if self.use_tls:
                # Newer Python versions (3.12+) use 'context' argument directly
                # Older ones might use 'ssl_context' or require more manual steps
                try:
                    self.connection.starttls(context=context)
                except TypeError:
                    # Fallback for even older versions or different smtplib implementations
                    self.connection.starttls()
            
            if self.username and self.password:
                self.connection.login(self.username, self.password)
                
            return True
        except Exception:
            if not self.fail_silently:
                raise
            return False
