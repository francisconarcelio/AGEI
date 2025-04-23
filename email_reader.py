import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from email_analyzer.email_connector import EmailProviderInterface
from email_analyzer.attachment_processor import AttachmentProcessor

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("email_reader")

class EmailReader:
    """
    Classe responsável por ler e-mails e extrair informações relevantes.
    """
    
    def __init__(self, email_provider: EmailProviderInterface):
        """
        Inicializa o leitor de e-mails.
        
        Args:
            email_provider: Provedor de e-mail para conexão
        """
        self.email_provider = email_provider
        self.attachment_processor = AttachmentProcessor()
    
    def read_emails(self, limit: int = 10, process_attachments: bool = True) -> List[Dict[str, Any]]:
        """
        Lê e-mails não lidos e extrai informações relevantes.
        
        Args:
            limit: Número máximo de e-mails a serem lidos
            process_attachments: Se deve processar anexos
            
        Returns:
            List[Dict[str, Any]]: Lista de e-mails processados
        """
        processed_emails = []
        
        try:
            # Conecta ao provedor de e-mail
            if not self.email_provider.connect():
                logger.error("Falha ao conectar ao provedor de e-mail")
                return []
            
            # Obtém e-mails não lidos
            emails = self.email_provider.get_unread_emails(limit=limit)
            
            # Processa cada e-mail
            for email_data in emails:
                try:
                    # Processa o e-mail
                    processed_email = self._process_email(email_data, process_attachments)
                    processed_emails.append(processed_email)
                    
                    # Marca o e-mail como lido
                    self.email_provider.mark_as_read(email_data['id'])
                
                except Exception as e:
                    logger.error(f"Erro ao processar e-mail {email_data.get('id', 'desconhecido')}: {str(e)}")
            
            return processed_emails
        
        except Exception as e:
            logger.error(f"Erro ao ler e-mails: {str(e)}")
            return []
        
        finally:
            # Desconecta do provedor de e-mail
            self.email_provider.disconnect()
    
    def _process_email(self, email_data: Dict[str, Any], process_attachments: bool) -> Dict[str, Any]:
        """
        Processa um e-mail e extrai informações relevantes.
        
        Args:
            email_data: Dados do e-mail
            process_attachments: Se deve processar anexos
            
        Returns:
            Dict[str, Any]: E-mail processado com informações extraídas
        """
        # Cria cópia do e-mail para não modificar o original
        processed_email = email_data.copy()
        
        # Extrai entidades do corpo do e-mail
        body = email_data.get('body', '')
        
        # Adiciona informações extraídas
        processed_email['extracted_info'] = self._extract_information(body)
        
        # Processa anexos se necessário
        if process_attachments and 'attachments' in email_data:
            processed_attachments = []
            
            for attachment in email_data['attachments']:
                processed_attachment = self.attachment_processor.process_attachment(attachment)
                
                # Adiciona informações extraídas do anexo
                if 'text' in processed_attachment:
                    attachment_info = self._extract_information(processed_attachment['text'])
                    processed_attachment['extracted_info'] = attachment_info
                    
                    # Combina informações extraídas do anexo com as do e-mail
                    self._combine_extracted_info(processed_email['extracted_info'], attachment_info)
                
                processed_attachments.append(processed_attachment)
            
            processed_email['processed_attachments'] = processed_attachments
        
        # Determina a relevância do e-mail para contratos escolares
        processed_email['relevance'] = self._determine_relevance(processed_email)
        
        return processed_email
    
    def _extract_information(self, text: str) -> Dict[str, Any]:
        """
        Extrai informações relevantes de um texto.
        
        Args:
            text: Texto a ser analisado
            
        Returns:
            Dict[str, Any]: Informações extraídas
        """
        # Utiliza os métodos de extração do PDFProcessor
        from email_analyzer.attachment_processor import PDFProcessor
        pdf_processor = PDFProcessor()
        
        contract_numbers = pdf_processor._extract_contract_numbers(text)
        school_names = pdf_processor._extract_school_names(text)
        dates = pdf_processor._extract_dates(text)
        
        # Extrai outras informações relevantes
        # Aqui poderiam ser adicionadas mais extrações específicas
        
        return {
            'contract_numbers': contract_numbers,
            'school_names': school_names,
            'dates': dates
        }
    
    def _combine_extracted_info(self, target: Dict[str, List[str]], source: Dict[str, List[str]]) -> None:
        """
        Combina informações extraídas de diferentes fontes.
        
        Args:
            target: Dicionário de destino
            source: Dicionário de origem
        """
        for key, values in source.items():
            if key in target:
                # Combina listas e remove duplicatas
                target[key] = list(set(target[key] + values))
            else:
                target[key] = values
    
    def _determine_relevance(self, email: Dict[str, Any]) -> float:
        """
        Determina a relevância do e-mail para contratos escolares.
        
        Args:
            email: E-mail processado
            
        Returns:
            float: Pontuação de relevância (0.0 a 1.0)
        """
        relevance = 0.0
        extracted_info = email.get('extracted_info', {})
        
        # Verifica se há números de contrato
        contract_numbers = extracted_info.get('contract_numbers', [])
        if contract_numbers:
            relevance += 0.4
        
        # Verifica se há nomes de escolas
        school_names = extracted_info.get('school_names', [])
        if school_names:
            relevance += 0.4
        
        # Verifica se há datas
        dates = extracted_info.get('dates', [])
        if dates:
            relevance += 0.1
        
        # Verifica palavras-chave no assunto
        subject = email.get('subject', '').lower()
        keywords = ['contrato', 'escola', 'educação', 'ensino', 'acordo', 'termo', 'aditivo']
        
        for keyword in keywords:
            if keyword in subject:
                relevance += 0.1
                break
        
        # Limita a relevância a 1.0
        return min(relevance, 1.0)

# Exemplo de uso
if __name__ == "__main__":
    from email_analyzer.email_connector import EmailProviderFactory
    
    # Configuração de exemplo
    config = {
        'server': 'imap.example.com',
        'username': 'user@example.com',
        'password': 'password',
        'port': 993,
        'use_ssl': True
    }
    
    # Cria provedor de e-mail
    provider = EmailProviderFactory.create_provider('imap', config)
    
    # Cria leitor de e-mails
    reader = EmailReader(provider)
    
    # Lê e-mails
    emails = reader.read_emails(limit=5)
    
    # Exibe informações
    for email in emails:
        print(f"Assunto: {email['subject']}")
        print(f"Relevância: {email['relevance']:.2f}")
        print(f"Informações extraídas: {email['extracted_info']}")
        print("-" * 50)
