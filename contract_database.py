import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
import datetime
import sqlite3
from pathlib import Path

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("contract_database")

class ContractDatabase:
    """
    Classe responsável pelo gerenciamento do banco de dados de contratos escolares.
    """
    
    def __init__(self, db_path: Optional[str] = None, config_path: Optional[str] = None):
        """
        Inicializa o banco de dados de contratos.
        
        Args:
            db_path: Caminho para o arquivo de banco de dados SQLite (opcional)
            config_path: Caminho para o arquivo de configuração (opcional)
        """
        # Carrega configuração
        self.config = self._load_config(config_path)
        
        # Configuração do banco de dados
        self.db_config = self.config.get('database', {})
        
        # Caminho para o banco de dados
        self.db_path = db_path or self.db_config.get('db_path', 'contracts.db')
        
        # Inicializa banco de dados
        self._init_database()
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do banco de dados.
        
        Args:
            config_path: Caminho para o arquivo de configuração
            
        Returns:
            Dict[str, Any]: Configuração carregada
        """
        # Configuração padrão
        default_config = {
            'database': {
                'db_path': 'contracts.db',
                'backup_enabled': True,
                'backup_interval': 86400,  # 24 horas em segundos
                'backup_path': 'backups/',
                'max_backups': 7
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
    
    def _init_database(self) -> None:
        """
        Inicializa o banco de dados, criando tabelas se necessário.
        """
        try:
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Cria tabela de contratos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contracts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_number TEXT UNIQUE NOT NULL,
                    school_name TEXT NOT NULL,
                    contract_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    value TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # Cria tabela de histórico de contratos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contract_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT,
                    timestamp TEXT NOT NULL,
                    user TEXT,
                    FOREIGN KEY (contract_id) REFERENCES contracts (id)
                )
            ''')
            
            # Cria tabela de escolas
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schools (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    zip_code TEXT,
                    phone TEXT,
                    email TEXT,
                    contact_person TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')
            
            # Cria tabela de pagamentos
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    contract_id INTEGER NOT NULL,
                    amount TEXT NOT NULL,
                    payment_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (contract_id) REFERENCES contracts (id)
                )
            ''')
            
            # Cria índices para melhorar performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_number ON contracts (contract_number)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_school_name ON contracts (school_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON contracts (status)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contract_history_contract_id ON contract_history (contract_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_payments_contract_id ON payments (contract_id)')
            
            # Commit e fecha conexão
            conn.commit()
            conn.close()
            
            logger.info("Banco de dados inicializado com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
            raise
    
    def add_contract(self, contract_data: Dict[str, Any], user: Optional[str] = None) -> Dict[str, Any]:
        """
        Adiciona um novo contrato ao banco de dados.
        
        Args:
            contract_data: Dados do contrato
            user: Usuário que está realizando a operação (opcional)
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se o número do contrato já existe
            cursor.execute('SELECT id FROM contracts WHERE contract_number = ?', (contract_data.get('contract_number'),))
            if cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'message': f"Contrato com número '{contract_data.get('contract_number')}' já existe"
                }
            
            # Prepara dados do contrato
            now = datetime.datetime.now().isoformat()
            
            # Insere contrato
            cursor.execute('''
                INSERT INTO contracts (
                    contract_number, school_name, contract_type, status,
                    value, start_date, end_date, description,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                contract_data.get('contract_number', ''),
                contract_data.get('school_name', ''),
                contract_data.get('contract_type', ''),
                contract_data.get('status', ''),
                contract_data.get('value', ''),
                contract_data.get('start_date', ''),
                contract_data.get('end_date', ''),
                contract_data.get('description', ''),
                now,
                now
            ))
            
            # Obtém ID do contrato inserido
            contract_id = cursor.lastrowid
            
            # Registra histórico
            cursor.execute('''
                INSERT INTO contract_history (
                    contract_id, action, details, timestamp, user
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                contract_id,
                'create',
                f"Contrato criado com número '{contract_data.get('contract_number')}'",
                now,
                user
            ))
            
            # Commit e fecha conexão
            conn.commit()
            conn.close()
            
            # Faz backup se necessário
            self._backup_if_needed()
            
            return {
                'success': True,
                'message': f"Contrato '{contract_data.get('contract_number')}' adicionado com sucesso",
                'contract_id': contract_id
            }
        
        except Exception as e:
            logger.error(f"Erro ao adicionar contrato: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao adicionar contrato: {str(e)}"
            }
    
    def update_contract(self, contract_data: Dict[str, Any], user: Optional[str] = None) -> Dict[str, Any]:
        """
        Atualiza um contrato existente.
        
        Args:
            contract_data: Dados do contrato
            user: Usuário que está realizando a operação (opcional)
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se o contrato existe
            cursor.execute('SELECT id FROM contracts WHERE contract_number = ?', (contract_data.get('contract_number'),))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {
                    'success': False,
                    'message': f"Contrato com número '{contract_data.get('contract_number')}' não encontrado"
                }
            
            contract_id = result[0]
            
            # Prepara dados do contrato
            now = datetime.datetime.now().isoformat()
            
            # Atualiza contrato
            cursor.execute('''
                UPDATE contracts SET
                    school_name = ?,
                    contract_type = ?,
                    status = ?,
                    value = ?,
                    start_date = ?,
                    end_date = ?,
                    description = ?,
                    updated_at = ?
                WHERE id = ?
            ''', (
                contract_data.get('school_name', ''),
                contract_data.get('contract_type', ''),
                contract_data.get('status', ''),
                contract_data.get('value', ''),
                contract_data.get('start_date', ''),
                contract_data.get('end_date', ''),
                contract_data.get('description', ''),
                now,
                contract_id
            ))
            
            # Registra histórico
            cursor.execute('''
                INSERT INTO contract_history (
                    contract_id, action, details, timestamp, user
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                contract_id,
                'update',
                f"Contrato atualizado com número '{contract_data.get('contract_number')}'",
                now,
                user
            ))
            
            # Commit e fecha conexão
            conn.commit()
            conn.close()
            
            # Faz backup se necessário
            self._backup_if_needed()
            
            return {
                'success': True,
                'message': f"Contrato '{contract_data.get('contract_number')}' atualizado com sucesso",
                'contract_id': contract_id
            }
        
        except Exception as e:
            logger.error(f"Erro ao atualizar contrato: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao atualizar contrato: {str(e)}"
            }
    
    def delete_contract(self, contract_number: str, user: Optional[str] = None) -> Dict[str, Any]:
        """
        Remove um contrato.
        
        Args:
            contract_number: Número do contrato
            user: Usuário que está realizando a operação (opcional)
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se o contrato existe
            cursor.execute('SELECT id FROM contracts WHERE contract_number = ?', (contract_number,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return {
                    'success': False,
                    'message': f"Contrato com número '{contract_number}' não encontrado"
                }
            
            contract_id = result[0]
            
            # Prepara dados
            now = datetime.datetime.now().isoformat()
            
            # Registra histórico antes de remover
            cursor.execute('''
                INSERT INTO contract_history (
                    contract_id, action, details, timestamp, user
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                contract_id,
                'delete',
                f"Contrato removido com número '{contract_number}'",
                now,
                user
            ))
            
            # Remove pagamentos associados
            cursor.execute('DELETE FROM payments WHERE contract_id = ?', (contract_id,))
            
            # Remove contrato
            cursor.execute('DELETE FROM contracts WHERE id = ?', (contract_id,))
            
            # Commit e fecha conexão
            conn.commit()
            conn.close()
            
            # Faz backup se necessário
            self._backup_if_needed()
            
            return {
                'success': True,
                'message': f"Contrato '{contract_number}' removido com sucesso"
            }
        
        except Exception as e:
            logger.error(f"Erro ao remover contrato: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao remover contrato: {str(e)}"
            }
    
    def get_contract(self, contract_number: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um contrato pelo número.
        
        Args:
            contract_number: Número do contrato
            
        Returns:
            Optional[Dict[str, Any]]: Contrato encontrado ou None
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para retornar resultados como dicionários
            cursor = conn.cursor()
            
            # Busca contrato
            cursor.execute('''
                SELECT * FROM contracts WHERE contract_number = ?
            ''', (contract_number,))
            
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return None
            
            # Converte para dicionário
            contract = dict(result)
            
            # Busca histórico do contrato
            cursor.execute('''
                SELECT * FROM contract_history WHERE contract_id = ? ORDER BY timestamp DESC
            ''', (contract['id'],))
            
            history = [dict(row) for row in cursor.fetchall()]
            contract['history'] = history
            
            # Busca pagamentos do contrato
            cursor.execute('''
                SELECT * FROM payments WHERE contract_id = ? ORDER BY payment_date DESC
            ''', (contract['id'],))
            
            payments = [dict(row) for row in cursor.fetchall()]
            contract['payments'] = payments
            
            # Fecha conexão
            conn.close()
            
            return contract
        
        except Exception as e:
            logger.error(f"Erro ao obter contrato: {str(e)}")
            return None
    
    def search_contracts(self, search_term: Optional[str] = None, 
                        status: Optional[str] = None, 
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        limit: int = 100) -> List[Dict[str, Any]]:
        """
        Pesquisa contratos.
        
        Args:
            search_term: Termo de pesquisa (opcional)
            status: Status do contrato (opcional)
            start_date: Data de início (opcional)
            end_date: Data de término (opcional)
            limit: Limite de resultados
            
        Returns:
            List[Dict[str, Any]]: Lista de contratos encontrados
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para retornar resultados como dicionários
            cursor = conn.cursor()
            
            # Constrói consulta
            query = 'SELECT * FROM contracts WHERE 1=1'
            params = []
            
            if search_term:
                query += ''' AND (
                    contract_number LIKE ? OR
                    school_name LIKE ? OR
                    description LIKE ?
                )'''
                search_pattern = f'%{search_term}%'
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if start_date:
                query += ' AND start_date >= ?'
                params.append(start_date)
            
            if end_date:
                query += ' AND end_date <= ?'
                params.append(end_date)
            
            query += ' ORDER BY updated_at DESC LIMIT ?'
            params.append(limit)
            
            # Executa consulta
            cursor.execute(query, params)
            
            # Converte resultados para lista de dicionários
            contracts = [dict(row) for row in cursor.fetchall()]
            
            # Fecha conexão
            conn.close()
            
            return contracts
        
        except Exception as e:
            logger.error(f"Erro ao pesquisar contratos: {str(e)}")
            return []
    
    def add_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adiciona um pagamento a um contrato.
        
        Args:
            payment_data: Dados do pagamento
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se o contrato existe
            contract_id = payment_data.get('contract_id')
            
            if isinstance(contract_id, str) and not contract_id.isdigit():
                # Se for um número de contrato em vez de ID
                cursor.execute('SELECT id FROM contracts WHERE contract_number = ?', (contract_id,))
                result = cursor.fetchone()
                
                if not result:
                    conn.close()
                    return {
                        'success': False,
                        'message': f"Contrato com número '{contract_id}' não encontrado"
                    }
                
                contract_id = result[0]
            
            # Verifica se o contrato existe pelo ID
            cursor.execute('SELECT id FROM contracts WHERE id = ?', (contract_id,))
            if not cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'message': f"Contrato com ID {contract_id} não encontrado"
                }
            
            # Prepara dados do pagamento
            now = datetime.datetime.now().isoformat()
            
            # Insere pagamento
            cursor.execute('''
                INSERT INTO payments (
                    contract_id, amount, payment_date, status, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                contract_id,
                payment_data.get('amount', ''),
                payment_data.get('payment_date', now),
                payment_data.get('status', 'pendente'),
                payment_data.get('description', ''),
                now
            ))
            
            # Obtém ID do pagamento inserido
            payment_id = cursor.lastrowid
            
            # Registra histórico
            cursor.execute('''
                INSERT INTO contract_history (
                    contract_id, action, details, timestamp, user
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                contract_id,
                'payment',
                f"Pagamento de {payment_data.get('amount', '')} registrado",
                now,
                payment_data.get('user')
            ))
            
            # Commit e fecha conexão
            conn.commit()
            conn.close()
            
            # Faz backup se necessário
            self._backup_if_needed()
            
            return {
                'success': True,
                'message': f"Pagamento registrado com sucesso",
                'payment_id': payment_id
            }
        
        except Exception as e:
            logger.error(f"Erro ao adicionar pagamento: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao adicionar pagamento: {str(e)}"
            }
    
    def add_school(self, school_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adiciona uma escola ao banco de dados.
        
        Args:
            school_data: Dados da escola
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Verifica se a escola já existe
            cursor.execute('SELECT id FROM schools WHERE name = ?', (school_data.get('name'),))
            if cursor.fetchone():
                conn.close()
                return {
                    'success': False,
                    'message': f"Escola com nome '{school_data.get('name')}' já existe"
                }
            
            # Prepara dados da escola
            now = datetime.datetime.now().isoformat()
            
            # Insere escola
            cursor.execute('''
                INSERT INTO schools (
                    name, address, city, state, zip_code, phone, email, contact_person,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                school_data.get('name', ''),
                school_data.get('address', ''),
                school_data.get('city', ''),
                school_data.get('state', ''),
                school_data.get('zip_code', ''),
                school_data.get('phone', ''),
                school_data.get('email', ''),
                school_data.get('contact_person', ''),
                now,
                now
            ))
            
            # Obtém ID da escola inserida
            school_id = cursor.lastrowid
            
            # Commit e fecha conexão
            conn.commit()
            conn.close()
            
            # Faz backup se necessário
            self._backup_if_needed()
            
            return {
                'success': True,
                'message': f"Escola '{school_data.get('name')}' adicionada com sucesso",
                'school_id': school_id
            }
        
        except Exception as e:
            logger.error(f"Erro ao adicionar escola: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao adicionar escola: {str(e)}"
            }
    
    def get_schools(self, search_term: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Obtém lista de escolas.
        
        Args:
            search_term: Termo de pesquisa (opcional)
            limit: Limite de resultados
            
        Returns:
            List[Dict[str, Any]]: Lista de escolas
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para retornar resultados como dicionários
            cursor = conn.cursor()
            
            # Constrói consulta
            query = 'SELECT * FROM schools'
            params = []
            
            if search_term:
                query += ' WHERE name LIKE ? OR city LIKE ? OR state LIKE ?'
                search_pattern = f'%{search_term}%'
                params.extend([search_pattern, search_pattern, search_pattern])
            
            query += ' ORDER BY name LIMIT ?'
            params.append(limit)
            
            # Executa consulta
            cursor.execute(query, params)
            
            # Converte resultados para lista de dicionários
            schools = [dict(row) for row in cursor.fetchall()]
            
            # Fecha conexão
            conn.close()
            
            return schools
        
        except Exception as e:
            logger.error(f"Erro ao obter escolas: {str(e)}")
            return []
    
    def get_contract_history(self, contract_id: int) -> List[Dict[str, Any]]:
        """
        Obtém histórico de um contrato.
        
        Args:
            contract_id: ID do contrato
            
        Returns:
            List[Dict[str, Any]]: Histórico do contrato
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para retornar resultados como dicionários
            cursor = conn.cursor()
            
            # Busca histórico
            cursor.execute('''
                SELECT * FROM contract_history WHERE contract_id = ? ORDER BY timestamp DESC
            ''', (contract_id,))
            
            # Converte resultados para lista de dicionários
            history = [dict(row) for row in cursor.fetchall()]
            
            # Fecha conexão
            conn.close()
            
            return history
        
        except Exception as e:
            logger.error(f"Erro ao obter histórico de contrato: {str(e)}")
            return []
    
    def get_contract_payments(self, contract_id: int) -> List[Dict[str, Any]]:
        """
        Obtém pagamentos de um contrato.
        
        Args:
            contract_id: ID do contrato
            
        Returns:
            List[Dict[str, Any]]: Pagamentos do contrato
        """
        try:
            # Conecta ao banco de dados
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Para retornar resultados como dicionários
            cursor = conn.cursor()
            
            # Busca pagamentos
            cursor.execute('''
                SELECT * FROM payments WHERE contract_id = ? ORDER BY payment_date DESC
            ''', (contract_id,))
            
            # Converte resultados para lista de dicionários
            payments = [dict(row) for row in cursor.fetchall()]
            
            # Fecha conexão
            conn.close()
            
            return payments
        
        except Exception as e:
            logger.error(f"Erro ao obter pagamentos de contrato: {str(e)}")
            return []
    
    def _backup_if_needed(self) -> bool:
        """
        Faz backup do banco de dados se necessário.
        
        Returns:
            bool: True se o backup foi realizado, False caso contrário
        """
        try:
            # Verifica se backup está habilitado
            if not self.db_config.get('backup_enabled', True):
                return False
            
            # Verifica se é hora de fazer backup
            backup_path = self.db_config.get('backup_path', 'backups/')
            
            # Cria diretório de backup se não existir
            os.makedirs(backup_path, exist_ok=True)
            
            # Verifica último backup
            backup_files = sorted([f for f in os.listdir(backup_path) if f.startswith('contracts_') and f.endswith('.db')])
            
            if not backup_files:
                # Nenhum backup encontrado, faz o primeiro
                return self._create_backup()
            
            # Verifica data do último backup
            last_backup = backup_files[-1]
            last_backup_path = os.path.join(backup_path, last_backup)
            
            if not os.path.exists(last_backup_path):
                return self._create_backup()
            
            # Verifica intervalo de backup
            backup_interval = self.db_config.get('backup_interval', 86400)  # 24 horas em segundos
            last_backup_time = os.path.getmtime(last_backup_path)
            current_time = datetime.datetime.now().timestamp()
            
            if current_time - last_backup_time >= backup_interval:
                return self._create_backup()
            
            return False
        
        except Exception as e:
            logger.error(f"Erro ao verificar necessidade de backup: {str(e)}")
            return False
    
    def _create_backup(self) -> bool:
        """
        Cria um backup do banco de dados.
        
        Returns:
            bool: True se o backup foi criado com sucesso, False caso contrário
        """
        try:
            # Obtém caminho de backup
            backup_path = self.db_config.get('backup_path', 'backups/')
            
            # Cria diretório de backup se não existir
            os.makedirs(backup_path, exist_ok=True)
            
            # Gera nome do arquivo de backup
            backup_filename = f"contracts_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_file_path = os.path.join(backup_path, backup_filename)
            
            # Copia banco de dados
            import shutil
            shutil.copy2(self.db_path, backup_file_path)
            
            logger.info(f"Backup do banco de dados criado em {backup_file_path}")
            
            # Limpa backups antigos
            self._clean_old_backups()
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao criar backup: {str(e)}")
            return False
    
    def _clean_old_backups(self) -> None:
        """
        Remove backups antigos, mantendo apenas os mais recentes.
        """
        try:
            # Obtém configurações
            backup_path = self.db_config.get('backup_path', 'backups/')
            max_backups = self.db_config.get('max_backups', 7)
            
            # Lista arquivos de backup
            backup_files = sorted([f for f in os.listdir(backup_path) if f.startswith('contracts_') and f.endswith('.db')])
            
            # Remove backups excedentes
            if len(backup_files) > max_backups:
                files_to_remove = backup_files[:-max_backups]
                
                for file in files_to_remove:
                    file_path = os.path.join(backup_path, file)
                    os.remove(file_path)
                    logger.info(f"Backup antigo removido: {file_path}")
        
        except Exception as e:
            logger.error(f"Erro ao limpar backups antigos: {str(e)}")

# Exemplo de uso
if __name__ == "__main__":
    # Cria banco de dados
    db = ContractDatabase()
    
    # Adiciona um contrato de exemplo
    result = db.add_contract({
        'contract_number': 'CONT-2023-001',
        'school_name': 'Escola Municipal João da Silva',
        'contract_type': 'Fornecimento de Software',
        'status': 'Ativo',
        'value': 'R$ 5.000,00',
        'start_date': '01/01/2023',
        'end_date': '31/12/2023',
        'description': 'Contrato de fornecimento de software de gestão escolar'
    }, user='admin')
    
    print(result)
    
    # Pesquisa contratos
    contracts = db.search_contracts(search_term='João')
    
    for contract in contracts:
        print(f"{contract['contract_number']} - {contract['school_name']} - {contract['status']}")
