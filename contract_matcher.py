import os
import logging
from typing import Dict, List, Any, Optional, Tuple
import json
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("contract_matcher")

class ContractMatcher:
    """
    Classe responsável por associar e-mails a contratos existentes.
    """
    
    def __init__(self, contracts_db_path: Optional[str] = None):
        """
        Inicializa o associador de contratos.
        
        Args:
            contracts_db_path: Caminho para o arquivo de banco de dados de contratos (opcional)
        """
        self.contracts_db_path = contracts_db_path
        self.contracts = []
        self.vectorizer = CountVectorizer(ngram_range=(1, 2), stop_words='english')
        
        # Carrega contratos se o caminho for fornecido
        if contracts_db_path:
            self._load_contracts()
    
    def _load_contracts(self) -> None:
        """Carrega contratos do banco de dados."""
        try:
            if not os.path.exists(self.contracts_db_path):
                logger.warning(f"Arquivo de banco de dados de contratos não encontrado: {self.contracts_db_path}")
                return
            
            with open(self.contracts_db_path, 'r') as f:
                self.contracts = json.load(f)
            
            logger.info(f"Carregados {len(self.contracts)} contratos do banco de dados")
        
        except Exception as e:
            logger.error(f"Erro ao carregar contratos: {str(e)}")
            self.contracts = []
    
    def match_contract(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Associa um e-mail a contratos existentes.
        
        Args:
            email: E-mail a ser associado
            
        Returns:
            Dict[str, Any]: E-mail com informações de contratos associados
        """
        try:
            # Cria cópia do e-mail para não modificar o original
            matched_email = email.copy()
            
            # Se não houver contratos, retorna o e-mail original
            if not self.contracts:
                matched_email['matched_contracts'] = []
                matched_email['has_contract_match'] = False
                return matched_email
            
            # Extrai entidades do e-mail
            entities = email.get('entities', {})
            
            # Tenta associar por número de contrato
            contract_numbers = entities.get('contract_numbers', [])
            if contract_numbers:
                exact_matches = self._match_by_contract_number(contract_numbers)
                if exact_matches:
                    matched_email['matched_contracts'] = exact_matches
                    matched_email['has_contract_match'] = True
                    matched_email['match_method'] = 'contract_number'
                    return matched_email
            
            # Tenta associar por nome de escola
            school_names = entities.get('school_names', [])
            if school_names:
                school_matches = self._match_by_school_name(school_names)
                if school_matches:
                    matched_email['matched_contracts'] = school_matches
                    matched_email['has_contract_match'] = True
                    matched_email['match_method'] = 'school_name'
                    return matched_email
            
            # Tenta associar por similaridade de texto
            text_matches = self._match_by_text_similarity(email)
            if text_matches:
                matched_email['matched_contracts'] = text_matches
                matched_email['has_contract_match'] = True
                matched_email['match_method'] = 'text_similarity'
                return matched_email
            
            # Se não houver correspondências
            matched_email['matched_contracts'] = []
            matched_email['has_contract_match'] = False
            
            return matched_email
        
        except Exception as e:
            logger.error(f"Erro ao associar e-mail a contratos: {str(e)}")
            # Retorna o e-mail original sem correspondências
            email['matched_contracts'] = []
            email['has_contract_match'] = False
            email['match_error'] = str(e)
            return email
    
    def _match_by_contract_number(self, contract_numbers: List[str]) -> List[Dict[str, Any]]:
        """
        Associa por número de contrato.
        
        Args:
            contract_numbers: Lista de números de contrato
            
        Returns:
            List[Dict[str, Any]]: Lista de contratos correspondentes
        """
        matches = []
        
        for contract in self.contracts:
            contract_number = contract.get('contract_number', '')
            if contract_number and any(num == contract_number for num in contract_numbers):
                # Cria cópia do contrato e adiciona score de correspondência
                match = contract.copy()
                match['match_score'] = 1.0  # Correspondência exata
                matches.append(match)
        
        # Ordena por score (maior primeiro)
        matches.sort(key=lambda x: x.get('match_score', 0.0), reverse=True)
        
        return matches
    
    def _match_by_school_name(self, school_names: List[str]) -> List[Dict[str, Any]]:
        """
        Associa por nome de escola.
        
        Args:
            school_names: Lista de nomes de escolas
            
        Returns:
            List[Dict[str, Any]]: Lista de contratos correspondentes
        """
        matches = []
        
        for contract in self.contracts:
            school_name = contract.get('school_name', '')
            if not school_name:
                continue
            
            # Calcula similaridade com cada nome de escola
            for name in school_names:
                similarity = self._calculate_name_similarity(name, school_name)
                
                # Se a similaridade for alta o suficiente
                if similarity >= 0.8:
                    # Cria cópia do contrato e adiciona score de correspondência
                    match = contract.copy()
                    match['match_score'] = similarity
                    matches.append(match)
                    break  # Passa para o próximo contrato
        
        # Ordena por score (maior primeiro)
        matches.sort(key=lambda x: x.get('match_score', 0.0), reverse=True)
        
        return matches
    
    def _match_by_text_similarity(self, email: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Associa por similaridade de texto.
        
        Args:
            email: E-mail a ser associado
            
        Returns:
            List[Dict[str, Any]]: Lista de contratos correspondentes
        """
        # Extrai texto do e-mail
        email_text = self._extract_text_for_matching(email)
        
        # Se não houver texto suficiente, retorna lista vazia
        if len(email_text.split()) < 10:
            return []
        
        matches = []
        
        # Prepara textos para vetorização
        texts = [email_text]
        for contract in self.contracts:
            contract_text = self._extract_contract_text(contract)
            texts.append(contract_text)
        
        # Vetoriza textos
        try:
            X = self.vectorizer.fit_transform(texts)
            
            # Calcula similaridade entre o e-mail e cada contrato
            email_vector = X[0]
            contract_vectors = X[1:]
            
            # Calcula similaridade de cosseno
            similarities = cosine_similarity(email_vector, contract_vectors).flatten()
            
            # Adiciona contratos com similaridade alta
            for i, similarity in enumerate(similarities):
                if similarity >= 0.3:  # Limiar de similaridade
                    # Cria cópia do contrato e adiciona score de correspondência
                    match = self.contracts[i].copy()
                    match['match_score'] = float(similarity)
                    matches.append(match)
            
            # Ordena por score (maior primeiro)
            matches.sort(key=lambda x: x.get('match_score', 0.0), reverse=True)
            
            # Limita o número de correspondências
            return matches[:5]
        
        except Exception as e:
            logger.error(f"Erro ao calcular similaridade de texto: {str(e)}")
            return []
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calcula a similaridade entre dois nomes.
        
        Args:
            name1: Primeiro nome
            name2: Segundo nome
            
        Returns:
            float: Score de similaridade (0.0 a 1.0)
        """
        # Normaliza nomes (converte para minúsculas e remove espaços extras)
        name1 = ' '.join(name1.lower().split())
        name2 = ' '.join(name2.lower().split())
        
        # Correspondência exata
        if name1 == name2:
            return 1.0
        
        # Um nome contém o outro
        if name1 in name2 or name2 in name1:
            return 0.9
        
        # Calcula similaridade de tokens
        tokens1 = set(name1.split())
        tokens2 = set(name2.split())
        
        # Interseção de tokens
        common_tokens = tokens1.intersection(tokens2)
        
        # Calcula similaridade de Jaccard
        if not tokens1 or not tokens2:
            return 0.0
        
        similarity = len(common_tokens) / len(tokens1.union(tokens2))
        
        return similarity
    
    def _extract_text_for_matching(self, email: Dict[str, Any]) -> str:
        """
        Extrai texto de um e-mail para correspondência.
        
        Args:
            email: E-mail
            
        Returns:
            str: Texto extraído
        """
        texts = []
        
        # Adiciona assunto
        subject = email.get('subject', '')
        if subject:
            texts.append(subject)
        
        # Adiciona corpo
        body = email.get('body', '')
        if body:
            texts.append(body)
        
        # Adiciona entidades extraídas
        entities = email.get('entities', {})
        for entity_type, values in entities.items():
            if values:
                entity_text = f"{entity_type}: {', '.join(values)}"
                texts.append(entity_text)
        
        # Combina todos os textos
        return "\n\n".join(texts)
    
    def _extract_contract_text(self, contract: Dict[str, Any]) -> str:
        """
        Extrai texto de um contrato para correspondência.
        
        Args:
            contract: Contrato
            
        Returns:
            str: Texto extraído
        """
        texts = []
        
        # Adiciona número do contrato
        contract_number = contract.get('contract_number', '')
        if contract_number:
            texts.append(f"Contrato: {contract_number}")
        
        # Adiciona nome da escola
        school_name = contract.get('school_name', '')
        if school_name:
            texts.append(f"Escola: {school_name}")
        
        # Adiciona descrição
        description = contract.get('description', '')
        if description:
            texts.append(description)
        
        # Adiciona outros campos relevantes
        for field in ['type', 'status', 'value', 'start_date', 'end_date']:
            value = contract.get(field, '')
            if value:
                texts.append(f"{field}: {value}")
        
        # Combina todos os textos
        return "\n\n".join(texts)

# Exemplo de uso
if __name__ == "__main__":
    # Exemplo de contratos
    contracts = [
        {
            'contract_number': '12345',
            'school_name': 'Escola Municipal João da Silva',
            'type': 'Fornecimento de Software',
            'status': 'Ativo',
            'value': 'R$ 5.000,00',
            'start_date': '01/01/2023',
            'end_date': '31/12/2023',
            'description': 'Contrato de fornecimento de software de gestão escolar'
        },
        {
            'contract_number': '67890',
            'school_name': 'Colégio Estadual Maria Oliveira',
            'type': 'Suporte Técnico',
            'status': 'Ativo',
            'value': 'R$ 3.000,00',
            'start_date': '01/03/2023',
            'end_date': '28/02/2024',
            'description': 'Contrato de suporte técnico para sistema de gestão escolar'
        }
    ]
    
    # Salva contratos em arquivo temporário
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        json.dump(contracts, f)
        contracts_db_path = f.name
    
    # Cria matcher
    matcher = ContractMatcher(contracts_db_path)
    
    # Exemplo de e-mail
    email = {
        'subject': 'Renovação de Contrato - Escola João da Silva',
        'body': '''
        Prezados,
        
        Solicito a renovação do contrato nº 12345 da Escola Municipal João da Silva.
        O contrato atual vence em 31/12/2023 e gostaríamos de renová-lo por mais 12 meses.
        
        O valor atual é de R$ 5.000,00 mensais.
        
        Atenciosamente,
        Maria Oliveira
        Diretora
        Tel: (11) 98765-4321
        ''',
        'entities': {
            'contract_numbers': ['12345'],
            'school_names': ['Escola Municipal João da Silva'],
            'dates': ['31/12/2023'],
            'value': ['R$ 5.000,00']
        }
    }
    
    # Associa e-mail a contratos
    matched_email = matcher.match_contract(email)
    
    # Exibe resultados
    print(f"Correspondência encontrada: {matched_email['has_contract_match']}")
    print(f"Método de correspondência: {matched_email.get('match_method', 'N/A')}")
    
    for contract in matched_email.get('matched_contracts', []):
        print(f"Contrato: {contract['contract_number']} - {contract['school_name']}")
        print(f"Score: {contract.get('match_score', 0.0):.2f}")
        print("-" * 50)
    
    # Remove arquivo temporário
    os.unlink(contracts_db_path)
