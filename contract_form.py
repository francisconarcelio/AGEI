import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
import gradio as gr
from pathlib import Path
import datetime

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("contract_form")

class ContractForm:
    """
    Classe responsável pela interface de formulário para gerenciamento de contratos escolares.
    """
    
    def __init__(self, config_path: Optional[str] = None, contracts_db_path: Optional[str] = None):
        """
        Inicializa o formulário de contratos.
        
        Args:
            config_path: Caminho para o arquivo de configuração (opcional)
            contracts_db_path: Caminho para o banco de dados de contratos (opcional)
        """
        # Carrega configuração
        self.config = self._load_config(config_path)
        
        # Configuração do formulário
        self.form_config = self.config.get('contract_form', {})
        
        # Caminho para o banco de dados de contratos
        self.contracts_db_path = contracts_db_path or self.form_config.get('contracts_db_path', 'contracts.json')
        
        # Carrega contratos
        self.contracts = self._load_contracts()
        
        # Inicializa interface
        self.interface = None
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """
        Carrega configuração do formulário.
        
        Args:
            config_path: Caminho para o arquivo de configuração
            
        Returns:
            Dict[str, Any]: Configuração carregada
        """
        # Configuração padrão
        default_config = {
            'contract_form': {
                'title': 'Gerenciamento de Contratos Escolares',
                'theme': 'default',
                'contracts_db_path': 'contracts.json',
                'contract_types': [
                    'Fornecimento de Software',
                    'Suporte Técnico',
                    'Consultoria',
                    'Treinamento',
                    'Manutenção',
                    'Licenciamento',
                    'Outro'
                ],
                'contract_statuses': [
                    'Em Análise',
                    'Pendente',
                    'Ativo',
                    'Suspenso',
                    'Cancelado',
                    'Finalizado'
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
    
    def _load_contracts(self) -> List[Dict[str, Any]]:
        """
        Carrega contratos do banco de dados.
        
        Returns:
            List[Dict[str, Any]]: Lista de contratos
        """
        try:
            if not os.path.exists(self.contracts_db_path):
                logger.warning(f"Arquivo de banco de dados de contratos não encontrado: {self.contracts_db_path}")
                return []
            
            with open(self.contracts_db_path, 'r') as f:
                contracts = json.load(f)
            
            logger.info(f"Carregados {len(contracts)} contratos do banco de dados")
            return contracts
        
        except Exception as e:
            logger.error(f"Erro ao carregar contratos: {str(e)}")
            return []
    
    def _save_contracts(self) -> bool:
        """
        Salva contratos no banco de dados.
        
        Returns:
            bool: True se os contratos foram salvos com sucesso, False caso contrário
        """
        try:
            # Cria diretório se não existir
            os.makedirs(os.path.dirname(os.path.abspath(self.contracts_db_path)), exist_ok=True)
            
            with open(self.contracts_db_path, 'w') as f:
                json.dump(self.contracts, f, indent=2)
            
            logger.info(f"Salvos {len(self.contracts)} contratos no banco de dados")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao salvar contratos: {str(e)}")
            return False
    
    def _add_contract(self, contract_number: str, school_name: str, contract_type: str,
                     status: str, value: str, start_date: str, end_date: str,
                     description: str) -> Dict[str, Any]:
        """
        Adiciona um novo contrato.
        
        Args:
            contract_number: Número do contrato
            school_name: Nome da escola
            contract_type: Tipo do contrato
            status: Status do contrato
            value: Valor do contrato
            start_date: Data de início
            end_date: Data de término
            description: Descrição do contrato
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Verifica se o número do contrato já existe
            for contract in self.contracts:
                if contract.get('contract_number') == contract_number:
                    return {
                        'success': False,
                        'message': f"Contrato com número '{contract_number}' já existe"
                    }
            
            # Cria novo contrato
            new_contract = {
                'contract_number': contract_number,
                'school_name': school_name,
                'type': contract_type,
                'status': status,
                'value': value,
                'start_date': start_date,
                'end_date': end_date,
                'description': description,
                'created_at': datetime.datetime.now().isoformat(),
                'updated_at': datetime.datetime.now().isoformat()
            }
            
            # Adiciona à lista de contratos
            self.contracts.append(new_contract)
            
            # Salva contratos
            if self._save_contracts():
                return {
                    'success': True,
                    'message': f"Contrato '{contract_number}' adicionado com sucesso"
                }
            else:
                return {
                    'success': False,
                    'message': "Erro ao salvar contrato no banco de dados"
                }
        
        except Exception as e:
            logger.error(f"Erro ao adicionar contrato: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao adicionar contrato: {str(e)}"
            }
    
    def _update_contract(self, contract_number: str, school_name: str, contract_type: str,
                        status: str, value: str, start_date: str, end_date: str,
                        description: str) -> Dict[str, Any]:
        """
        Atualiza um contrato existente.
        
        Args:
            contract_number: Número do contrato
            school_name: Nome da escola
            contract_type: Tipo do contrato
            status: Status do contrato
            value: Valor do contrato
            start_date: Data de início
            end_date: Data de término
            description: Descrição do contrato
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Procura contrato pelo número
            for i, contract in enumerate(self.contracts):
                if contract.get('contract_number') == contract_number:
                    # Atualiza contrato
                    self.contracts[i] = {
                        'contract_number': contract_number,
                        'school_name': school_name,
                        'type': contract_type,
                        'status': status,
                        'value': value,
                        'start_date': start_date,
                        'end_date': end_date,
                        'description': description,
                        'created_at': contract.get('created_at', datetime.datetime.now().isoformat()),
                        'updated_at': datetime.datetime.now().isoformat()
                    }
                    
                    # Salva contratos
                    if self._save_contracts():
                        return {
                            'success': True,
                            'message': f"Contrato '{contract_number}' atualizado com sucesso"
                        }
                    else:
                        return {
                            'success': False,
                            'message': "Erro ao salvar contrato no banco de dados"
                        }
            
            # Se não encontrou o contrato
            return {
                'success': False,
                'message': f"Contrato com número '{contract_number}' não encontrado"
            }
        
        except Exception as e:
            logger.error(f"Erro ao atualizar contrato: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao atualizar contrato: {str(e)}"
            }
    
    def _delete_contract(self, contract_number: str) -> Dict[str, Any]:
        """
        Remove um contrato.
        
        Args:
            contract_number: Número do contrato
            
        Returns:
            Dict[str, Any]: Resultado da operação
        """
        try:
            # Procura contrato pelo número
            for i, contract in enumerate(self.contracts):
                if contract.get('contract_number') == contract_number:
                    # Remove contrato
                    del self.contracts[i]
                    
                    # Salva contratos
                    if self._save_contracts():
                        return {
                            'success': True,
                            'message': f"Contrato '{contract_number}' removido com sucesso"
                        }
                    else:
                        return {
                            'success': False,
                            'message': "Erro ao salvar banco de dados após remoção"
                        }
            
            # Se não encontrou o contrato
            return {
                'success': False,
                'message': f"Contrato com número '{contract_number}' não encontrado"
            }
        
        except Exception as e:
            logger.error(f"Erro ao remover contrato: {str(e)}")
            return {
                'success': False,
                'message': f"Erro ao remover contrato: {str(e)}"
            }
    
    def _search_contracts(self, search_term: str) -> List[Dict[str, Any]]:
        """
        Pesquisa contratos.
        
        Args:
            search_term: Termo de pesquisa
            
        Returns:
            List[Dict[str, Any]]: Lista de contratos encontrados
        """
        try:
            if not search_term:
                return self.contracts
            
            search_term = search_term.lower()
            results = []
            
            for contract in self.contracts:
                # Pesquisa em vários campos
                if (search_term in contract.get('contract_number', '').lower() or
                    search_term in contract.get('school_name', '').lower() or
                    search_term in contract.get('type', '').lower() or
                    search_term in contract.get('status', '').lower() or
                    search_term in contract.get('description', '').lower()):
                    results.append(contract)
            
            return results
        
        except Exception as e:
            logger.error(f"Erro ao pesquisar contratos: {str(e)}")
            return []
    
    def _get_contract_by_number(self, contract_number: str) -> Optional[Dict[str, Any]]:
        """
        Obtém um contrato pelo número.
        
        Args:
            contract_number: Número do contrato
            
        Returns:
            Optional[Dict[str, Any]]: Contrato encontrado ou None
        """
        for contract in self.contracts:
            if contract.get('contract_number') == contract_number:
                return contract
        
        return None
    
    def launch(self, share: bool = False) -> None:
        """
        Inicia o formulário de contratos.
        
        Args:
            share: Se deve compartilhar o formulário publicamente
        """
        # Título do formulário
        title = self.form_config.get('title', 'Gerenciamento de Contratos Escolares')
        
        # Tema
        theme = self.form_config.get('theme', 'default')
        
        # Opções de tipo e status
        contract_types = self.form_config.get('contract_types', [])
        contract_statuses = self.form_config.get('contract_statuses', [])
        
        # Cria interface
        with gr.Blocks(title=title, theme=theme) as interface:
            gr.Markdown(f"# {title}")
            
            with gr.Tabs():
                with gr.TabItem("Pesquisar Contratos"):
                    with gr.Row():
                        search_term = gr.Textbox(label="Pesquisar", placeholder="Digite para pesquisar...")
                        search_button = gr.Button("Pesquisar")
                    
                    contracts_table = gr.Dataframe(
                        headers=["Número", "Escola", "Tipo", "Status", "Valor", "Início", "Término"],
                        datatype=["str", "str", "str", "str", "str", "str", "str"],
                        label="Contratos"
                    )
                    
                    # Função de pesquisa
                    def search_func(search_term):
                        results = self._search_contracts(search_term)
                        
                        # Formata resultados para tabela
                        table_data = []
                        for contract in results:
                            table_data.append([
                                contract.get('contract_number', ''),
                                contract.get('school_name', ''),
                                contract.get('type', ''),
                                contract.get('status', ''),
                                contract.get('value', ''),
                                contract.get('start_date', ''),
                                contract.get('end_date', '')
                            ])
                        
                        return table_data
                    
                    # Configura pesquisa
                    search_button.click(
                        fn=search_func,
                        inputs=[search_term],
                        outputs=[contracts_table]
                    )
                    
                    # Pesquisa inicial
                    interface.load(
                        fn=lambda: search_func(""),
                        inputs=None,
                        outputs=[contracts_table]
                    )
                
                with gr.TabItem("Adicionar/Editar Contrato"):
                    with gr.Row():
                        with gr.Column():
                            contract_number = gr.Textbox(label="Número do Contrato", placeholder="Ex: CONT-2023-001")
                            school_name = gr.Textbox(label="Nome da Escola", placeholder="Ex: Escola Municipal João da Silva")
                            contract_type = gr.Dropdown(label="Tipo do Contrato", choices=contract_types, value=contract_types[0] if contract_types else None)
                            status = gr.Dropdown(label="Status", choices=contract_statuses, value=contract_statuses[0] if contract_statuses else None)
                        
                        with gr.Column():
                            value = gr.Textbox(label="Valor", placeholder="Ex: R$ 5.000,00")
                            start_date = gr.Textbox(label="Data de Início", placeholder="Ex: 01/01/2023")
                            end_date = gr.Textbox(label="Data de Término", placeholder="Ex: 31/12/2023")
                            description = gr.Textbox(label="Descrição", placeholder="Descrição do contrato", lines=5)
                    
                    with gr.Row():
                        load_button = gr.Button("Carregar Contrato")
                        add_button = gr.Button("Adicionar Contrato")
                        update_button = gr.Button("Atualizar Contrato")
                        delete_button = gr.Button("Remover Contrato")
                    
                    result = gr.Textbox(label="Resultado", interactive=False)
                    
                    # Função para carregar contrato
                    def load_func(contract_number):
                        contract = self._get_contract_by_number(contract_number)
                        
                        if not contract:
                            return [
                                contract_number, "", "", "", "", "", "", "",
                                "Contrato não encontrado"
                            ]
                        
                        return [
                            contract.get('contract_number', ''),
                            contract.get('school_name', ''),
                            contract.get('type', ''),
                            contract.get('status', ''),
                            contract.get('value', ''),
                            contract.get('start_date', ''),
                            contract.get('end_date', ''),
                            contract.get('description', ''),
                            f"Contrato '{contract_number}' carregado com sucesso"
                        ]
                    
                    # Função para adicionar contrato
                    def add_func(contract_number, school_name, contract_type, status, value, start_date, end_date, description):
                        result = self._add_contract(
                            contract_number=contract_number,
                            school_name=school_name,
                            contract_type=contract_type,
                            status=status,
                            value=value,
                            start_date=start_date,
                            end_date=end_date,
                            description=description
                        )
                        
                        return result['message']
                    
                    # Função para atualizar contrato
                    def update_func(contract_number, school_name, contract_type, status, value, start_date, end_date, description):
                        result = self._update_contract(
                            contract_number=contract_number,
                            school_name=school_name,
                            contract_type=contract_type,
                            status=status,
                            value=value,
                            start_date=start_date,
                            end_date=end_date,
                            description=description
                        )
                        
                        return result['message']
                    
                    # Função para remover contrato
                    def delete_func(contract_number):
                        result = self._delete_contract(contract_number=contract_number)
                        return result['message']
                    
                    # Configura botões
                    load_button.click(
                        fn=load_func,
                        inputs=[contract_number],
                        outputs=[
                            contract_number, school_name, contract_type, status,
                            value, start_date, end_date, description, result
                        ]
                    )
                    
                    add_button.click(
                        fn=add_func,
                        inputs=[
                            contract_number, school_name, contract_type, status,
                            value, start_date, end_date, description
                        ],
                        outputs=[result]
                    )
                    
                    update_button.click(
                        fn=update_func,
                        inputs=[
                            contract_number, school_name, contract_type, status,
                            value, start_date, end_date, description
                        ],
                        outputs=[result]
                    )
                    
                    delete_button.click(
                        fn=delete_func,
                        inputs=[contract_number],
                        outputs=[result]
                    )
        
        # Salva referência à interface
        self.interface = interface
        
        # Inicia interface
        interface.launch(share=share)

# Exemplo de uso
if __name__ == "__main__":
    # Cria formulário
    form = ContractForm()
    
    # Inicia formulário
    form.launch()
