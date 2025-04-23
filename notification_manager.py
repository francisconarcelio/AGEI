import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
from pathlib import Path
import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("notification_manager")

class NotificationManager:
    """
    Classe responsável por gerenciar notificações para usuários do sistema.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o gerenciador de notificações.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        # Carrega configuração
        self.config = self._load_config(config_path)
        
        # Configuração de notificações
        self.notification_config = self.config.get('notification', {})
        
        # Histórico de notificações
        self.notification_history = []
        
        # Carrega histórico se existir
        history_path = self.notification_config.get('history_path', 'notification_history.json')
        if os.path.exists(history_path):
            try:
                with open(history_path, 'r') as f:
                    self.notification_history = json.load(f)
            except Exception as e:
                logger.error(f"Erro ao carregar histórico de notificações: {str(e)}")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do gerenciador.
        
        Args:
            config_path: Caminho para o arquivo de configuração
            
        Returns:
            Dict[str, Any]: Configuração carregada
        """
        # Configuração padrão
        default_config = {
            'notification': {
                'history_path': 'notification_history.json',
                'max_history': 1000,
                'email_notifications': True,
                'dashboard_notifications': True,
                'sms_notifications': False,
                'notification_levels': {
                    'info': True,
                    'warning': True,
                    'error': True,
                    'critical': True
                }
            },
            'users': {
                'admin': {
                    'email': 'admin@empresa.com',
                    'phone': '',
                    'notification_levels': ['info', 'warning', 'error', 'critical']
                },
                'comercial': {
                    'email': 'comercial@empresa.com',
                    'phone': '',
                    'notification_levels': ['warning', 'error', 'critical']
                },
                'juridico': {
                    'email': 'juridico@empresa.com',
                    'phone': '',
                    'notification_levels': ['warning', 'error', 'critical']
                },
                'financeiro': {
                    'email': 'financeiro@empresa.com',
                    'phone': '',
                    'notification_levels': ['warning', 'error', 'critical']
                },
                'atendimento': {
                    'email': 'atendimento@empresa.com',
                    'phone': '',
                    'notification_levels': ['warning', 'error', 'critical']
                },
                'suporte_tecnico': {
                    'email': 'suporte@empresa.com',
                    'phone': '',
                    'notification_levels': ['warning', 'error', 'critical']
                }
            },
            'templates': {
                'email': {
                    'subject': '[{level}] {title}',
                    'body': '''
                        <html>
                        <body>
                        <h2>{title}</h2>
                        <p><strong>Nível:</strong> {level}</p>
                        <p><strong>Data:</strong> {date}</p>
                        <p><strong>Mensagem:</strong> {message}</p>
                        
                        {details}
                        
                        <hr>
                        <p>Esta é uma notificação automática do Sistema de Contratos.</p>
                        </body>
                        </html>
                    '''
                },
                'sms': {
                    'body': '[{level}] {title}: {message}'
                },
                'dashboard': {
                    'title': '[{level}] {title}',
                    'body': '{message}'
                }
            }
        }
        
        # Se não houver caminho de configuração, retorna configuração padrão
        if not config_path:
            logger.warning("Nenhum arquivo de configuração fornecido, usando configuração padrão")
            return default_config
        
        try:
            # Carrega configuração do arquivo
            with open(config_path, 'r') as file:
                config = json.load(file)
            
            logger.info(f"Configuração carregada de {config_path}")
            
            # Mescla com configuração padrão para garantir que todos os campos existam
            for section, values in default_config.items():
                if section not in config:
                    config[section] = values
                else:
                    if isinstance(values, dict):
                        for key, value in values.items():
                            if key not in config[section]:
                                config[section][key] = value
            
            return config
        
        except Exception as e:
            logger.error(f"Erro ao carregar configuração de {config_path}: {str(e)}")
            logger.warning("Usando configuração padrão")
            return default_config
    
    def notify(self, title: str, message: str, level: str = 'info', 
              department: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> bool:
        """
        Envia uma notificação.
        
        Args:
            title: Título da notificação
            message: Mensagem da notificação
            level: Nível da notificação ('info', 'warning', 'error', 'critical')
            department: Departamento destinatário (opcional)
            details: Detalhes adicionais (opcional)
            
        Returns:
            bool: True se a notificação foi enviada com sucesso, False caso contrário
        """
        try:
            # Verifica se o nível de notificação está habilitado
            if not self.notification_config.get('notification_levels', {}).get(level, True):
                logger.info(f"Notificações de nível '{level}' estão desabilitadas")
                return False
            
            # Cria notificação
            notification = {
                'title': title,
                'message': message,
                'level': level,
                'department': department,
                'details': details or {},
                'date': datetime.datetime.now().isoformat(),
                'id': len(self.notification_history) + 1
            }
            
            # Adiciona ao histórico
            self.notification_history.append(notification)
            
            # Limita tamanho do histórico
            max_history = self.notification_config.get('max_history', 1000)
            if len(self.notification_history) > max_history:
                self.notification_history = self.notification_history[-max_history:]
            
            # Salva histórico
            self._save_history()
            
            # Envia notificações
            success = True
            
            # Notificações por e-mail
            if self.notification_config.get('email_notifications', True):
                email_success = self._send_email_notification(notification)
                success = success and email_success
            
            # Notificações por SMS
            if self.notification_config.get('sms_notifications', False):
                sms_success = self._send_sms_notification(notification)
                success = success and sms_success
            
            # Notificações no dashboard
            if self.notification_config.get('dashboard_notifications', True):
                dashboard_success = self._add_dashboard_notification(notification)
                success = success and dashboard_success
            
            return success
        
        except Exception as e:
            logger.error(f"Erro ao enviar notificação: {str(e)}")
            return False
    
    def _save_history(self) -> bool:
        """
        Salva histórico de notificações.
        
        Returns:
            bool: True se o histórico foi salvo com sucesso, False caso contrário
        """
        try:
            history_path = self.notification_config.get('history_path', 'notification_history.json')
            
            with open(history_path, 'w') as f:
                json.dump(self.notification_history, f, indent=2)
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao salvar histórico de notificações: {str(e)}")
            return False
    
    def _send_email_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Envia notificação por e-mail.
        
        Args:
            notification: Notificação a ser enviada
            
        Returns:
            bool: True se a notificação foi enviada com sucesso, False caso contrário
        """
        try:
            # Determina destinatários
            recipients = []
            
            # Se houver departamento específico
            department = notification.get('department')
            if department and department in self.config.get('users', {}):
                user = self.config['users'][department]
                
                # Verifica se o nível de notificação está habilitado para o usuário
                if notification['level'] in user.get('notification_levels', []):
                    email = user.get('email')
                    if email:
                        recipients.append(email)
            
            # Adiciona admin para notificações críticas
            if notification['level'] == 'critical':
                admin_email = self.config.get('users', {}).get('admin', {}).get('email')
                if admin_email and admin_email not in recipients:
                    recipients.append(admin_email)
            
            # Se não houver destinatários, não envia
            if not recipients:
                logger.warning("Nenhum destinatário encontrado para notificação por e-mail")
                return False
            
            # Formata notificação
            subject_template = self.config.get('templates', {}).get('email', {}).get('subject', '[{level}] {title}')
            body_template = self.config.get('templates', {}).get('email', {}).get('body', '')
            
            subject = subject_template.format(
                level=notification['level'].upper(),
                title=notification['title']
            )
            
            # Formata detalhes
            details_html = ''
            if notification.get('details'):
                details_html = '<h3>Detalhes:</h3><ul>'
                for key, value in notification['details'].items():
                    details_html += f'<li><strong>{key}:</strong> {value}</li>'
                details_html += '</ul>'
            
            body = body_template.format(
                title=notification['title'],
                level=notification['level'].upper(),
                date=datetime.datetime.fromisoformat(notification['date']).strftime('%d/%m/%Y %H:%M:%S'),
                message=notification['message'],
                details=details_html
            )
            
            # Aqui seria implementado o envio de e-mail
            # Como é apenas um exemplo, apenas logamos a ação
            logger.info(f"E-mail de notificação enviado para {', '.join(recipients)}")
            logger.info(f"Assunto: {subject}")
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao enviar notificação por e-mail: {str(e)}")
            return False
    
    def _send_sms_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Envia notificação por SMS.
        
        Args:
            notification: Notificação a ser enviada
            
        Returns:
            bool: True se a notificação foi enviada com sucesso, False caso contrário
        """
        try:
            # Determina destinatários
            recipients = []
            
            # Se houver departamento específico
            department = notification.get('department')
            if department and department in self.config.get('users', {}):
                user = self.config['users'][department]
                
                # Verifica se o nível de notificação está habilitado para o usuário
                if notification['level'] in user.get('notification_levels', []):
                    phone = user.get('phone')
                    if phone:
                        recipients.append(phone)
            
            # Adiciona admin para notificações críticas
            if notification['level'] == 'critical':
                admin_phone = self.config.get('users', {}).get('admin', {}).get('phone')
                if admin_phone and admin_phone not in recipients:
                    recipients.append(admin_phone)
            
            # Se não houver destinatários, não envia
            if not recipients:
                logger.warning("Nenhum destinatário encontrado para notificação por SMS")
                return False
            
            # Formata notificação
            body_template = self.config.get('templates', {}).get('sms', {}).get('body', '[{level}] {title}: {message}')
            
            body = body_template.format(
                level=notification['level'].upper(),
                title=notification['title'],
                message=notification['message']
            )
            
            # Aqui seria implementado o envio de SMS
            # Como é apenas um exemplo, apenas logamos a ação
            logger.info(f"SMS de notificação enviado para {', '.join(recipients)}")
            logger.info(f"Mensagem: {body}")
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao enviar notificação por SMS: {str(e)}")
            return False
    
    def _add_dashboard_notification(self, notification: Dict[str, Any]) -> bool:
        """
        Adiciona notificação ao dashboard.
        
        Args:
            notification: Notificação a ser adicionada
            
        Returns:
            bool: True se a notificação foi adicionada com sucesso, False caso contrário
        """
        try:
            # Formata notificação para dashboard
            title_template = self.config.get('templates', {}).get('dashboard', {}).get('title', '[{level}] {title}')
            body_template = self.config.get('templates', {}).get('dashboard', {}).get('body', '{message}')
            
            title = title_template.format(
                level=notification['level'].upper(),
                title=notification['title']
            )
            
            body = body_template.format(
                message=notification['message']
            )
            
            # Aqui seria implementada a adição ao dashboard
            # Como é apenas um exemplo, apenas logamos a ação
            logger.info(f"Notificação adicionada ao dashboard: {title}")
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao adicionar notificação ao dashboard: {str(e)}")
            return False
    
    def get_notifications(self, department: Optional[str] = None, 
                         level: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Obtém notificações do histórico.
        
        Args:
            department: Filtrar por departamento (opcional)
            level: Filtrar por nível (opcional)
            limit: Número máximo de notificações a retornar
            
        Returns:
            List[Dict[str, Any]]: Lista de notificações
        """
        try:
            # Filtra notificações
            filtered = self.notification_history
            
            if department:
                filtered = [n for n in filtered if n.get('department') == department]
            
            if level:
                filtered = [n for n in filtered if n.get('level') == level]
            
            # Ordena por data (mais recentes primeiro)
            filtered.sort(key=lambda x: x.get('date', ''), reverse=True)
            
            # Limita número de resultados
            return filtered[:limit]
        
        except Exception as e:
            logger.error(f"Erro ao obter notificações: {str(e)}")
            return []

# Exemplo de uso
if __name__ == "__main__":
    # Cria gerenciador de notificações
    notification_manager = NotificationManager()
    
    # Envia notificação
    notification_manager.notify(
        title="Novo contrato recebido",
        message="Um novo contrato foi recebido para a Escola Municipal João da Silva",
        level="info",
        department="comercial",
        details={
            "escola": "Escola Municipal João da Silva",
            "contrato": "12345",
            "valor": "R$ 5.000,00"
        }
    )
    
    # Obtém notificações
    notifications = notification_manager.get_notifications(limit=5)
    
    # Exibe notificações
    for notification in notifications:
        print(f"{notification['date']} - [{notification['level'].upper()}] {notification['title']}")
        print(f"Mensagem: {notification['message']}")
        print("-" * 50)
