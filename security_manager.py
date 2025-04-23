import os
import logging
import json
import hashlib
import secrets
import base64
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import datetime
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("security_manager")

class SecurityManager:
    """
    Classe responsável pelo gerenciamento de segurança do sistema.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inicializa o gerenciador de segurança.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        # Carrega configuração
        self.config = self._load_config(config_path)
        
        # Configuração de segurança
        self.security_config = self.config.get('security', {})
        
        # Inicializa sistema de criptografia
        self._init_encryption()
        
        # Carrega usuários
        self.users = self._load_users()
    
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
            'security': {
                'users_file': 'users.json',
                'encryption_key_file': 'encryption.key',
                'password_min_length': 8,
                'password_require_uppercase': True,
                'password_require_lowercase': True,
                'password_require_numbers': True,
                'password_require_special': True,
                'session_timeout': 3600,  # 1 hora em segundos
                'max_login_attempts': 5,
                'lockout_duration': 1800,  # 30 minutos em segundos
                'sensitive_fields': [
                    'value',
                    'payment_amount',
                    'email',
                    'phone'
                ]
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
    
    def _init_encryption(self) -> None:
        """
        Inicializa sistema de criptografia.
        """
        try:
            # Obtém caminho do arquivo de chave
            key_file = self.security_config.get('encryption_key_file', 'encryption.key')
            
            # Verifica se o arquivo de chave existe
            if os.path.exists(key_file):
                # Carrega chave existente
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                # Gera nova chave
                key = Fernet.generate_key()
                
                # Salva chave
                os.makedirs(os.path.dirname(os.path.abspath(key_file)), exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(key)
                
                logger.info(f"Nova chave de criptografia gerada e salva em {key_file}")
            
            # Inicializa Fernet com a chave
            self.fernet = Fernet(key)
            
            logger.info("Sistema de criptografia inicializado com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao inicializar sistema de criptografia: {str(e)}")
            raise
    
    def _load_users(self) -> Dict[str, Any]:
        """
        Carrega usuários do arquivo.
        
        Returns:
            Dict[str, Any]: Usuários carregados
        """
        try:
            # Obtém caminho do arquivo de usuários
            users_file = self.security_config.get('users_file', 'users.json')
            
            # Verifica se o arquivo existe
            if not os.path.exists(users_file):
                # Cria arquivo com usuário admin padrão
                default_users = {
                    'admin': {
                        'password_hash': self._hash_password('admin123'),
                        'salt': base64.b64encode(secrets.token_bytes(16)).decode('utf-8'),
                        'role': 'admin',
                        'name': 'Administrador',
                        'email': 'admin@empresa.com',
                        'created_at': datetime.datetime.now().isoformat(),
                        'last_login': None,
                        'login_attempts': 0,
                        'locked_until': None,
                        'active': True
                    }
                }
                
                # Salva usuários
                os.makedirs(os.path.dirname(os.path.abspath(users_file)), exist_ok=True)
                with open(users_file, 'w') as f:
                    json.dump(default_users, f, indent=2)
                
                logger.info(f"Arquivo de usuários criado com usuário admin padrão em {users_file}")
                
                return default_users
            
            # Carrega usuários do arquivo
            with open(users_file, 'r') as f:
                users = json.load(f)
            
            logger.info(f"Usuários carregados de {users_file}")
            
            return users
        
        except Exception as e:
            logger.error(f"Erro ao carregar usuários: {str(e)}")
            return {}
    
    def _save_users(self) -> bool:
        """
        Salva usuários no arquivo.
        
        Returns:
            bool: True se os usuários foram salvos com sucesso, False caso contrário
        """
        try:
            # Obtém caminho do arquivo de usuários
            users_file = self.security_config.get('users_file', 'users.json')
            
            # Salva usuários
            os.makedirs(os.path.dirname(os.path.abspath(users_file)), exist_ok=True)
            with open(users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            
            logger.info(f"Usuários salvos em {users_file}")
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao salvar usuários: {str(e)}")
            return False
    
    def _hash_password(self, password: str, salt: Optional[str] = None) -> str:
        """
        Gera hash de senha.
        
        Args:
            password: Senha
            salt: Salt para o hash (opcional)
            
        Returns:
            str: Hash da senha
        """
        try:
            # Gera salt se não fornecido
            if not salt:
                salt = secrets.token_hex(16)
            
            # Gera hash
            hash_obj = hashlib.sha256()
            hash_obj.update(f"{password}{salt}".encode('utf-8'))
            password_hash = hash_obj.hexdigest()
            
            return password_hash
        
        except Exception as e:
            logger.error(f"Erro ao gerar hash de senha: {str(e)}")
            raise
    
    def _validate_password_strength(self, password: str) -> Dict[str, Any]:
        """
        Valida força da senha.
        
        Args:
            password: Senha
            
        Returns:
            Dict[str, Any]: Resultado da validação
        """
        try:
            # Obtém configurações
            min_length = self.security_config.get('password_min_length', 8)
            require_uppercase = self.security_config.get('password_require_uppercase', True)
            require_lowercase = self.security_config.get('password_require_lowercase', True)
            require_numbers = self.security_config.get('password_require_numbers', True)
            require_special = self.security_config.get('password_require_special', True)
            
            # Valida comprimento
            if len(password) < min_length:
                return {
                    'valid': False,
                    'message': f"A senha deve ter pelo menos {min_length} caracteres"
                }
            
            # Valida maiúsculas
            if require_uppercase and not any(c.isupper() for c in password):
                return {
                    'valid': False,
                    'message': "A senha deve conter pelo menos uma letra maiúscula"
                }
            
            # Valida minúsculas
            if require_lowercase and not any(c.islower() for c in password):
                return {
                    'valid': False,
                    'message': "A senha deve conter pelo menos uma letra minúscula"
                }
            
            # Valida números
            if require_numbers and not any(c.isdigit() for c in password):
                return {
                    'valid': False,
                    'message': "A senha deve conter pelo menos um número"
                }
            
            # Valida caracteres especiais
            if require_special and not any(not c.isalnum() for c in password):
                return {
                    'valid': False,
                    'message': "A senha deve conter pelo menos um caractere especial"
                }
            
            return {
                'valid': True,
                'message': "Senha válida"
            }
        
        except Exception as e:
            logger.error(f"Erro ao validar força da senha: {str(e)}")
            return {
                'valid': False,
                'message': f"Erro ao validar senha: {str(e)}"
            }
    
    def encrypt_data(self, data: str) -> str:
        """
        Criptografa dados.
        
        Args:
            data: Dados a serem criptografados
            
        Returns:
            str: Dados criptografados em base64
        """
        try:
            # Criptografa dados
            encrypted_data = self.fernet.encrypt(data.encode('utf-8'))
            
            # Converte para base64
            return base64.b64encode(encrypted_data).decode('utf-8')
        
        except Exception as e:
            logger.error(f"Erro ao criptografar dados: {str(e)}")
            raise
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Descriptografa dados.
        
        Args:
            encrypted_data: Dados criptografados em base64
            
        Returns:
            str: Dados descriptografados
        """
        try:
            # Converte de base64
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # Descriptografa dados
            decrypted_data = self.fernet.decrypt(encrypted_bytes)
            
            return decrypted_data.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Erro ao descriptografar dados: {str(e)}")
            raise
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Criptografa campos sensíveis em um dicionário.
        
        Args:
            data: Dicionário com dados
            
        Returns:
            Dict[str, Any]: Dicionário com campos sensíveis criptografados
        """
        try:
            # Obtém lista de campos sensíveis
            sensitive_fields = self.security_config.get('sensitive_fields', [])
            
            # Cria cópia do dicionário
            encrypted_data = data.copy()
            
            # Criptografa campos sensíveis
            for field in sensitive_fields:
                if field in encrypted_data and encrypted_data[field]:
                    # Verifica se o campo já está criptografado
                    if not str(encrypted_data[field]).startswith('encrypted:'):
                        # Criptografa campo
                        encrypted_value = self.encrypt_data(str(encrypted_data[field]))
                        encrypted_data[field] = f"encrypted:{encrypted_value}"
            
            return encrypted_data
        
        except Exception as e:
            logger.error(f"Erro ao criptografar campos sensíveis: {str(e)}")
            return data
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Descriptografa campos sensíveis em um dicionário.
        
        Args:
            data: Dicionário com dados
            
        Returns:
            Dict[str, Any]: Dicionário com campos sensíveis descriptografados
        """
        try:
            # Obtém lista de campos sensíveis
            sensitive_fields = self.security_config.get('sensitive_fields', [])
            
            # Cria cópia do dicionário
            decrypted_data = data.copy()
            
            # Descriptografa campos sensíveis
            for field in sensitive_fields:
                if field in decrypted_data and decrypted_data[field]:
                    # Verifica se o campo está criptografado
                    if isinstance(decrypted_data[field], str) and decrypted_data[field].startswith('encrypted:'):
                        # Extrai valor criptografado
                        encrypted_value = decrypted_data[field][10:]  # Remove 'encrypted:'
                        
                        # Descriptografa campo
                        decrypted_value = self.decrypt_data(encrypted_value)
                        decrypted_data[field] = decrypted_value
            
            return decrypted_data
        
        except Exception as e:
            logger.error(f"Erro ao descriptografar campos sensíveis: {str(e)}")
            return data
    
    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Autentica um usuário.
        
        Args:
            username: Nome de usuário
            password: Senha
            
        Returns:
            Dict[str, Any]: Resultado da autenticação
        """
        try:
            # Verifica se o usuário existe
            if username not in self.users:
                return {
                    'success': False,
                    'message': "Usuário não encontrado"
                }
            
            # Obtém dados do usuário
            user = self.users[username]
            
            # Verifica se o usuário está ativo
            if not user.get('active', True):
                return {
                    'success': False,
                    'message': "Usuário inativo"
                }
            
            # Verifica se o usuário está bloqueado
            locked_until = user.get('locked_until')
            if locked_until:
                locked_until_dt = datetime.datetime.fromisoformat(locked_until)
                if locked_until_dt > datetime.datetime.now():
                    # Calcula tempo restante
                    remaining_time = (locked_until_dt - datetime.datetime.now()).total_seconds()
                    remaining_minutes = int(remaining_time / 60)
                    
                    return {
                        'success': False,
                        'message': f"Usuário bloqueado. Tente novamente em {remaining_minutes} minutos"
                    }
                else:
                    # Remove bloqueio
                    user['locked_until'] = None
                    user['login_attempts'] = 0
            
            # Verifica senha
            salt = user.get('salt', '')
            password_hash = self._hash_password(password, salt)
            
            if password_hash != user.get('password_hash', ''):
                # Incrementa tentativas de login
                user['login_attempts'] = user.get('login_attempts', 0) + 1
                
                # Verifica se deve bloquear o usuário
                max_attempts = self.security_config.get('max_login_attempts', 5)
                if user['login_attempts'] >= max_attempts:
                    # Bloqueia usuário
                    lockout_duration = self.security_config.get('lockout_duration', 1800)  # 30 minutos
                    locked_until = datetime.datetime.now() + datetime.timedelta(seconds=lockout_duration)
                    user['locked_until'] = locked_until.isoformat()
                    
                    # Salva usuários
                    self._save_users()
                    
                    return {
                        'success': False,
                        'message': f"Usuário bloqueado por {lockout_duration // 60} minutos devido a múltiplas tentativas de login"
                    }
                
                # Salva usuários
                self._save_users()
                
                return {
                    'success': False,
                    'message': "Senha incorreta",
                    'attempts_left': max_attempts - user['login_attempts']
                }
            
            # Autenticação bem-sucedida
            
            # Atualiza dados do usuário
            user['login_attempts'] = 0
            user['last_login'] = datetime.datetime.now().isoformat()
            
            # Gera token de sessão
            session_token = secrets.token_hex(32)
            session_expiry = datetime.datetime.now() + datetime.timedelta(seconds=self.security_config.get('session_timeout', 3600))
            
            user['session_token'] = session_token
            user['session_expiry'] = session_expiry.isoformat()
            
            # Salva usuários
            self._save_users()
            
            return {
                'success': True,
                'message': "Autenticação bem-sucedida",
                'user': {
                    'username': username,
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'role': user.get('role', ''),
                    'session_token': session_token,
                    'session_expiry': session_expiry.isoformat()
                }
            }
        
        except Exception as e:
            logger.error(f"Erro ao autenticar usuário: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao autenticar usuário: {str(e)}"
            }
    
    def validate_session(self, username: str, session_token: str) -> Dict[str, Any]:
        """
        Valida uma sessão de usuário.
        
        Args:
            username: Nome de usuário
            session_token: Token de sessão
            
        Returns:
            Dict[str, Any]: Resultado da validação
        """
        try:
            # Verifica se o usuário existe
            if username not in self.users:
                return {
                    'valid': False,
                    'message': "Usuário não encontrado"
                }
            
            # Obtém dados do usuário
            user = self.users[username]
            
            # Verifica se o usuário está ativo
            if not user.get('active', True):
                return {
                    'valid': False,
                    'message': "Usuário inativo"
                }
            
            # Verifica token de sessão
            if user.get('session_token') != session_token:
                return {
                    'valid': False,
                    'message': "Token de sessão inválido"
                }
            
            # Verifica expiração da sessão
            session_expiry = user.get('session_expiry')
            if not session_expiry:
                return {
                    'valid': False,
                    'message': "Sessão expirada"
                }
            
            session_expiry_dt = datetime.datetime.fromisoformat(session_expiry)
            if session_expiry_dt < datetime.datetime.now():
                return {
                    'valid': False,
                    'message': "Sessão expirada"
                }
            
            # Sessão válida
            return {
                'valid': True,
                'message': "Sessão válida",
                'user': {
                    'username': username,
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'role': user.get('role', ''),
                    'session_expiry': session_expiry
                }
            }
        
        except Exception as e:
            logger.error(f"Erro ao validar sessão: {str(e)}")
            return {
                'valid': False,
                'message': f"Erro ao validar sessão: {str(e)}"
            }
    
    def create_user(self, username: str, password: str, role: str, name: str, email: str) -> Dict[str, Any]:
        """
        Cria um novo usuário.
        
        Args:
            username: Nome de usuário
            password: Senha
            role: Papel do usuário
            name: Nome completo
            email: E-mail
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Verifica se o usuário já existe
            if username in self.users:
                return {
                    'success': False,
                    'message': f"Usuário '{username}' já existe"
                }
            
            # Valida força da senha
            password_validation = self._validate_password_strength(password)
            if not password_validation['valid']:
                return {
                    'success': False,
                    'message': password_validation['message']
                }
            
            # Gera salt
            salt = secrets.token_hex(16)
            
            # Gera hash da senha
            password_hash = self._hash_password(password, salt)
            
            # Cria usuário
            self.users[username] = {
                'password_hash': password_hash,
                'salt': salt,
                'role': role,
                'name': name,
                'email': email,
                'created_at': datetime.datetime.now().isoformat(),
                'last_login': None,
                'login_attempts': 0,
                'locked_until': None,
                'active': True
            }
            
            # Salva usuários
            if self._save_users():
                return {
                    'success': True,
                    'message': f"Usuário '{username}' criado com sucesso"
                }
            else:
                # Remove usuário se não foi possível salvar
                del self.users[username]
                
                return {
                    'success': False,
                    'message': "Erro ao salvar usuário"
                }
        
        except Exception as e:
            logger.error(f"Erro ao criar usuário: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao criar usuário: {str(e)}"
            }
    
    def update_user(self, username: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza um usuário existente.
        
        Args:
            username: Nome de usuário
            data: Dados a serem atualizados
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Verifica se o usuário existe
            if username not in self.users:
                return {
                    'success': False,
                    'message': f"Usuário '{username}' não encontrado"
                }
            
            # Obtém dados do usuário
            user = self.users[username]
            
            # Atualiza senha se fornecida
            if 'password' in data:
                # Valida força da senha
                password_validation = self._validate_password_strength(data['password'])
                if not password_validation['valid']:
                    return {
                        'success': False,
                        'message': password_validation['message']
                    }
                
                # Gera salt
                salt = secrets.token_hex(16)
                
                # Gera hash da senha
                password_hash = self._hash_password(data['password'], salt)
                
                # Atualiza senha
                user['password_hash'] = password_hash
                user['salt'] = salt
            
            # Atualiza outros campos
            for field in ['role', 'name', 'email', 'active']:
                if field in data:
                    user[field] = data[field]
            
            # Salva usuários
            if self._save_users():
                return {
                    'success': True,
                    'message': f"Usuário '{username}' atualizado com sucesso"
                }
            else:
                return {
                    'success': False,
                    'message': "Erro ao salvar usuário"
                }
        
        except Exception as e:
            logger.error(f"Erro ao atualizar usuário: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao atualizar usuário: {str(e)}"
            }
    
    def delete_user(self, username: str) -> Dict[str, Any]:
        """
        Remove um usuário.
        
        Args:
            username: Nome de usuário
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Verifica se o usuário existe
            if username not in self.users:
                return {
                    'success': False,
                    'message': f"Usuário '{username}' não encontrado"
                }
            
            # Remove usuário
            del self.users[username]
            
            # Salva usuários
            if self._save_users():
                return {
                    'success': True,
                    'message': f"Usuário '{username}' removido com sucesso"
                }
            else:
                return {
                    'success': False,
                    'message': "Erro ao salvar usuário"
                }
        
        except Exception as e:
            logger.error(f"Erro ao remover usuário: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao remover usuário: {str(e)}"
            }
    
    def get_users(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de usuários.
        
        Returns:
            List[Dict[str, Any]]: Lista de usuários
        """
        try:
            # Cria lista de usuários
            users_list = []
            
            for username, user in self.users.items():
                # Remove campos sensíveis
                user_data = {
                    'username': username,
                    'name': user.get('name', ''),
                    'email': user.get('email', ''),
                    'role': user.get('role', ''),
                    'created_at': user.get('created_at', ''),
                    'last_login': user.get('last_login', ''),
                    'active': user.get('active', True)
                }
                
                users_list.append(user_data)
            
            return users_list
        
        except Exception as e:
            logger.error(f"Erro ao obter lista de usuários: {str(e)}")
            return []
    
    def sanitize_input(self, input_str: str) -> str:
        """
        Sanitiza entrada de texto para prevenir injeção.
        
        Args:
            input_str: Texto de entrada
            
        Returns:
            str: Texto sanitizado
        """
        try:
            if not input_str:
                return ""
            
            # Remove caracteres potencialmente perigosos
            sanitized = re.sub(r'[<>\'";]', '', input_str)
            
            return sanitized
        
        except Exception as e:
            logger.error(f"Erro ao sanitizar entrada: {str(e)}")
            return ""
    
    def validate_access(self, username: str, resource: str, action: str) -> Dict[str, Any]:
        """
        Valida acesso a um recurso.
        
        Args:
            username: Nome de usuário
            resource: Recurso a ser acessado
            action: Ação a ser realizada
            
        Returns:
            Dict[str, Any]: Resultado da validação
        """
        try:
            # Verifica se o usuário existe
            if username not in self.users:
                return {
                    'allowed': False,
                    'message': "Usuário não encontrado"
                }
            
            # Obtém dados do usuário
            user = self.users[username]
            
            # Verifica se o usuário está ativo
            if not user.get('active', True):
                return {
                    'allowed': False,
                    'message': "Usuário inativo"
                }
            
            # Obtém papel do usuário
            role = user.get('role', '')
            
            # Define permissões por papel
            permissions = {
                'admin': {
                    'contracts': ['read', 'create', 'update', 'delete'],
                    'users': ['read', 'create', 'update', 'delete'],
                    'schools': ['read', 'create', 'update', 'delete'],
                    'payments': ['read', 'create', 'update', 'delete'],
                    'reports': ['read', 'create'],
                    'settings': ['read', 'update']
                },
                'manager': {
                    'contracts': ['read', 'create', 'update'],
                    'users': ['read'],
                    'schools': ['read', 'create', 'update'],
                    'payments': ['read', 'create', 'update'],
                    'reports': ['read', 'create'],
                    'settings': ['read']
                },
                'user': {
                    'contracts': ['read'],
                    'users': [],
                    'schools': ['read'],
                    'payments': ['read'],
                    'reports': ['read'],
                    'settings': []
                }
            }
            
            # Verifica se o papel existe
            if role not in permissions:
                return {
                    'allowed': False,
                    'message': f"Papel '{role}' não reconhecido"
                }
            
            # Verifica se o recurso existe
            if resource not in permissions[role]:
                return {
                    'allowed': False,
                    'message': f"Recurso '{resource}' não reconhecido"
                }
            
            # Verifica se a ação é permitida
            if action not in permissions[role][resource]:
                return {
                    'allowed': False,
                    'message': f"Ação '{action}' não permitida para o recurso '{resource}'"
                }
            
            # Acesso permitido
            return {
                'allowed': True,
                'message': "Acesso permitido"
            }
        
        except Exception as e:
            logger.error(f"Erro ao validar acesso: {str(e)}")
            return {
                'allowed': False,
                'message': f"Erro ao validar acesso: {str(e)}"
            }
    
    def log_security_event(self, event_type: str, username: str, details: Dict[str, Any]) -> None:
        """
        Registra evento de segurança.
        
        Args:
            event_type: Tipo de evento
            username: Nome de usuário
            details: Detalhes do evento
        """
        try:
            # Cria registro de evento
            event = {
                'timestamp': datetime.datetime.now().isoformat(),
                'event_type': event_type,
                'username': username,
                'details': details,
                'ip_address': details.get('ip_address', 'unknown')
            }
            
            # Obtém caminho do arquivo de log
            log_file = self.security_config.get('security_log_file', 'security.log')
            
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
            
            # Adiciona ao arquivo de log
            with open(log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
            
            logger.info(f"Evento de segurança registrado: {event_type} por {username}")
        
        except Exception as e:
            logger.error(f"Erro ao registrar evento de segurança: {str(e)}")

# Exemplo de uso
if __name__ == "__main__":
    # Cria gerenciador de segurança
    security_manager = SecurityManager()
    
    # Cria usuário
    result = security_manager.create_user(
        username="gerente",
        password="Senha@123",
        role="manager",
        name="Gerente de Contratos",
        email="gerente@empresa.com"
    )
    
    print(result)
    
    # Autentica usuário
    auth_result = security_manager.authenticate_user(
        username="gerente",
        password="Senha@123"
    )
    
    print(auth_result)
    
    # Valida acesso
    access_result = security_manager.validate_access(
        username="gerente",
        resource="contracts",
        action="read"
    )
    
    print(access_result)
    
    # Criptografa dados sensíveis
    data = {
        "contract_number": "CONT-2023-001",
        "school_name": "Escola Municipal João da Silva",
        "value": "R$ 5.000,00",
        "email": "escola@exemplo.com"
    }
    
    encrypted_data = security_manager.encrypt_sensitive_fields(data)
    print("Dados criptografados:", encrypted_data)
    
    # Descriptografa dados sensíveis
    decrypted_data = security_manager.decrypt_sensitive_fields(encrypted_data)
    print("Dados descriptografados:", decrypted_data)
