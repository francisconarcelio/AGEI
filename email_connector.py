import imaplib
import email
import os
import logging
import tempfile
from email.header import decode_header
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from abc import ABC, abstractmethod
import re
import ssl

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_connector")

class EmailProviderInterface(ABC):
    """Interface para provedores de e-mail."""
    
    @abstractmethod
    def connect(self) -> bool:
        """Conecta ao servidor de e-mail."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Desconecta do servidor de e-mail."""
        pass
    
    @abstractmethod
    def get_unread_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Obtém e-mails não lidos."""
        pass
    
    @abstractmethod
    def mark_as_read(self, email_id: str) -> bool:
        """Marca um e-mail como lido."""
        pass
    
    @abstractmethod
    def move_to_folder(self, email_id: str, folder: str) -> bool:
        """Move um e-mail para uma pasta específica."""
        pass

class IMAPEmailProvider(EmailProviderInterface):
    """Implementação de provedor de e-mail usando IMAP."""
    
    def __init__(self, server: str, username: str, password: str, port: int = 993, use_ssl: bool = True):
        """
        Inicializa o provedor IMAP.
        
        Args:
            server: Endereço do servidor IMAP
            username: Nome de usuário para autenticação
            password: Senha para autenticação
            port: Porta do servidor (padrão: 993 para SSL)
            use_ssl: Se deve usar SSL para conexão
        """
        self.server = server
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.mail = None
        self.connected = False
        
        # Validar parâmetros
        if not server or not username or not password:
            raise ValueError("Servidor, usuário e senha são obrigatórios")
    
    def connect(self) -> bool:
        """
        Conecta ao servidor IMAP.
        
        Returns:
            bool: True se a conexão foi bem-sucedida, False caso contrário
        """
        try:
            # Criar contexto SSL personalizado para lidar com certificados antigos
            if self.use_ssl:
                context = ssl.create_default_context()
                # Desativar verificação de certificado se necessário (não recomendado para produção)
                # context.check_hostname = False
                # context.verify_mode = ssl.CERT_NONE
                self.mail = imaplib.IMAP4_SSL(self.server, self.port, ssl_context=context)
            else:
                self.mail = imaplib.IMAP4(self.server, self.port)
            
            # Login
            self.mail.login(self.username, self.password)
            self.connected = True
            logger.info(f"Conectado com sucesso ao servidor IMAP: {self.server}")
            return True
        
        except (imaplib.IMAP4.error, ssl.SSLError, ConnectionRefusedError) as e:
            logger.error(f"Erro ao conectar ao servidor IMAP: {str(e)}")
            self.connected = False
            return False
    
    def disconnect(self) -> bool:
        """
        Desconecta do servidor IMAP.
        
        Returns:
            bool: True se a desconexão foi bem-sucedida, False caso contrário
        """
        if not self.connected or not self.mail:
            return True
        
        try:
            self.mail.logout()
            self.connected = False
            logger.info("Desconectado do servidor IMAP")
            return True
        
        except imaplib.IMAP4.error as e:
            logger.error(f"Erro ao desconectar do servidor IMAP: {str(e)}")
            return False
    
    def get_unread_emails(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém e-mails não lidos da caixa de entrada.
        
        Args:
            limit: Número máximo de e-mails a serem obtidos
        
        Returns:
            List[Dict[str, Any]]: Lista de e-mails não lidos com metadados
        """
        if not self.connected or not self.mail:
            logger.error("Não conectado ao servidor IMAP")
            return []
        
        emails = []
        
        try:
            # Seleciona a caixa de entrada
            status, messages = self.mail.select("INBOX")
            
            if status != 'OK':
                logger.error(f"Erro ao selecionar caixa de entrada: {messages}")
                return []
            
            # Busca e-mails não lidos
            status, messages = self.mail.search(None, 'UNSEEN')
            
            if status != 'OK':
                logger.error(f"Erro ao buscar e-mails não lidos: {messages}")
                return []
            
            # Obtém IDs de e-mails
            email_ids = messages[0].split()
            
            # Limita o número de e-mails
            if limit > 0:
                email_ids = email_ids[:limit]
            
            for email_id in email_ids:
                try:
                    status, msg_data = self.mail.fetch(email_id, "(RFC822)")
                    
                    if status != 'OK':
                        logger.error(f"Erro ao buscar e-mail {email_id}: {msg_data}")
                        continue
                    
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            # Processa o e-mail
                            email_data = self._process_email(response_part[1], email_id)
                            if email_data:
                                emails.append(email_data)
                
                except Exception as e:
                    logger.error(f"Erro ao processar e-mail {email_id}: {str(e)}")
            
            logger.info(f"Obtidos {len(emails)} e-mails não lidos")
            return emails
        
        except imaplib.IMAP4.error as e:
            logger.error(f"Erro ao obter e-mails não lidos: {str(e)}")
            return []
    
    def mark_as_read(self, email_id: str) -> bool:
        """
        Marca um e-mail como lido.
        
        Args:
            email_id: ID do e-mail a ser marcado
        
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário
        """
        if not self.connected or not self.mail:
            logger.error("Não conectado ao servidor IMAP")
            return False
        
        try:
            # Adiciona a flag \Seen ao e-mail
            self.mail.store(email_id, '+FLAGS', '\\Seen')
            logger.info(f"E-mail {email_id} marcado como lido")
            return True
        
        except imaplib.IMAP4.error as e:
            logger.error(f"Erro ao marcar e-mail {email_id} como lido: {str(e)}")
            return False
    
    def move_to_folder(self, email_id: str, folder: str) -> bool:
        """
        Move um e-mail para uma pasta específica.
        
        Args:
            email_id: ID do e-mail a ser movido
            folder: Nome da pasta de destino
        
        Returns:
            bool: True se a operação foi bem-sucedida, False caso contrário
        """
        if not self.connected or not self.mail:
            logger.error("Não conectado ao servidor IMAP")
            return False
        
        try:
            # Copia o e-mail para a pasta de destino
            result, data = self.mail.copy(email_id, folder)
            
            if result == 'OK':
                # Marca o e-mail original para exclusão
                self.mail.store(email_id, '+FLAGS', '\\Deleted')
                # Expurga os e-mails marcados para exclusão
                self.mail.expunge()
                logger.info(f"E-mail {email_id} movido para a pasta {folder}")
                return True
            else:
                logger.error(f"Erro ao copiar e-mail {email_id} para a pasta {folder}: {data}")
                return False
        
        except imaplib.IMAP4.error as e:
            logger.error(f"Erro ao mover e-mail {email_id} para a pasta {folder}: {str(e)}")
            return False
    
    def _process_email(self, raw_email: bytes, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Processa um e-mail bruto e extrai metadados e conteúdo.
        
        Args:
            raw_email: E-mail bruto em bytes
            email_id: ID do e-mail
        
        Returns:
            Optional[Dict[str, Any]]: Dicionário com metadados e conteúdo do e-mail, ou None em caso de erro
        """
        try:
            # Analisa o e-mail
            msg = email.message_from_bytes(raw_email)
            
            # Extrai metadados
            subject = self._decode_header(msg["Subject"])
            from_addr = self._decode_header(msg["From"])
            to_addr = self._decode_header(msg["To"])
            date = self._decode_header(msg["Date"])
            
            # Extrai corpo e anexos
            body, attachments = self._extract_content(msg)
            
            # Cria dicionário com informações do e-mail
            email_data = {
                "id": email_id.decode() if isinstance(email_id, bytes) else email_id,
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "date": date,
                "body": body,
                "attachments": attachments
            }
            
            return email_data
        
        except Exception as e:
            logger.error(f"Erro ao processar e-mail: {str(e)}")
            return None
    
    def _decode_header(self, header: Optional[str]) -> str:
        """
        Decodifica um cabeçalho de e-mail.
        
        Args:
            header: Cabeçalho a ser decodificado
        
        Returns:
            str: Cabeçalho decodificado
        """
        if not header:
            return ""
        
        try:
            decoded_header = decode_header(header)
            parts = []
            
            for part, encoding in decoded_header:
                if isinstance(part, bytes):
                    # Tenta decodificar com o encoding especificado, ou utf-8, ou latin-1 como fallback
                    try:
                        if encoding:
                            parts.append(part.decode(encoding))
                        else:
                            parts.append(part.decode('utf-8'))
                    except UnicodeDecodeError:
                        try:
                            parts.append(part.decode('latin-1'))
                        except UnicodeDecodeError:
                            parts.append(part.decode('utf-8', errors='replace'))
                else:
                    parts.append(part)
            
            return " ".join(parts)
        
        except Exception as e:
            logger.error(f"Erro ao decodificar cabeçalho: {str(e)}")
            return header
    
    def _extract_content(self, msg: email.message.Message) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Extrai o corpo e anexos de um e-mail.
        
        Args:
            msg: Mensagem de e-mail
        
        Returns:
            Tuple[str, List[Dict[str, Any]]]: Corpo do e-mail e lista de anexos
        """
        body = ""
        attachments = []
        
        # Se a mensagem é multipart
        if msg.is_multipart():
            # Itera sobre as partes
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                # Pula partes vazias ou multipart
                if part.get_payload(decode=True) is None:
                    continue
                
                # Verifica se é um anexo
                if "attachment" in content_disposition or "inline" in content_disposition:
                    # Extrai informações do anexo
                    filename = part.get_filename()
                    if not filename:
                        # Gera um nome de arquivo se não houver
                        ext = content_type.split('/')[-1]
                        filename = f"attachment-{len(attachments)}.{ext}"
                    
                    # Salva o anexo em um arquivo temporário
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp:
                        temp.write(part.get_payload(decode=True))
                        temp_path = temp.name
                    
                    # Adiciona informações do anexo à lista
                    attachments.append({
                        "filename": filename,
                        "content_type": content_type,
                        "size": os.path.getsize(temp_path),
                        "path": temp_path
                    })
                
                # Verifica se é texto
                elif content_type == "text/plain" and "attachment" not in content_disposition:
                    # Adiciona ao corpo do e-mail
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset()
                    
                    if charset:
                        try:
                            body += payload.decode(charset)
                        except UnicodeDecodeError:
                            body += payload.decode('utf-8', errors='replace')
                    else:
                        body += payload.decode('utf-8', errors='replace')
                
                # Verifica se é HTML
                elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                    # Adiciona ao corpo do e-mail se não houver texto plano
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset()
                    
                    if charset:
                        try:
                            body += payload.decode(charset)
                        except UnicodeDecodeError:
                            body += payload.decode('utf-8', errors='replace')
                    else:
                        body += payload.decode('utf-8', errors='replace')
        
        # Se a mensagem não é multipart
        else:
            # Extrai o corpo
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset()
            
            if charset:
                try:
                    body = payload.decode(charset)
                except UnicodeDecodeError:
                    body = payload.decode('utf-8', errors='replace')
            else:
                body = payload.decode('utf-8', errors='replace')
        
        return body, attachments

class EmailProviderFactory:
    """Fábrica para criar provedores de e-mail."""
    
    @staticmethod
    def create_provider(provider_type: str, config: Dict[str, Any]) -> EmailProviderInterface:
        """
        Cria um provedor de e-mail com base no tipo e configuração.
        
        Args:
            provider_type: Tipo de provedor ('imap', 'pop3', etc.)
            config: Configuração do provedor
        
        Returns:
            EmailProviderInterface: Instância do provedor de e-mail
        
        Raises:
            ValueError: Se o tipo de provedor não for suportado
        """
        if provider_type.lower() == 'imap':
            return IMAPEmailProvider(
                server=config.get('server', ''),
                username=config.get('username', ''),
                password=config.get('password', ''),
                port=config.get('port', 993),
                use_ssl=config.get('use_ssl', True)
            )
        else:
            raise ValueError(f"Tipo de provedor não suportado: {provider_type}")

# Exemplo de uso
if __name__ == "__main__":
    # Configuração de exemplo
    config = {
        'server': 'imap.example.com',
        'username': 'user@example.com',
        'password': 'password',
        'port': 993,
        'use_ssl': True
    }
    
    # Cria provedor
    provider = EmailProviderFactory.create_provider('imap', config)
    
    # Conecta ao servidor
    if provider.connect():
        try:
            # Obtém e-mails não lidos
            emails = provider.get_unread_emails(limit=5)
            
            # Processa e-mails
            for email_data in emails:
                print(f"Assunto: {email_data['subject']}")
                print(f"De: {email_data['from']}")
                print(f"Data: {email_data['date']}")
                print(f"Anexos: {len(email_data['attachments'])}")
                print("-" * 50)
                
                # Marca como lido
                provider.mark_as_read(email_data['id'])
        
        finally:
            # Desconecta do servidor
            provider.disconnect()
