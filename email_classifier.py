import os
import logging
import numpy as np
import pickle
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("classifier")

class EmailClassifier:
    """
    Classe responsável por classificar e-mails relacionados a contratos escolares.
    """
    
    def __init__(self, model_dir: str = 'models'):
        """
        Inicializa o classificador de e-mails.
        
        Args:
            model_dir: Diretório para armazenar/carregar modelos
        """
        self.model_dir = model_dir
        self.category_model = None
        self.priority_model = None
        self.department_model = None
        
        # Cria diretório de modelos se não existir
        os.makedirs(model_dir, exist_ok=True)
        
        # Tenta carregar modelos existentes
        self._load_models()
        
        # Mapeamento de categorias para departamentos
        self.category_to_department = {
            'novo_contrato': 'comercial',
            'renovacao': 'comercial',
            'alteracao': 'juridico',
            'cancelamento': 'juridico',
            'pagamento': 'financeiro',
            'duvida': 'atendimento',
            'reclamacao': 'atendimento',
            'suporte': 'suporte_tecnico',
            'outro': 'triagem'
        }
    
    def _load_models(self) -> None:
        """Carrega modelos treinados do disco."""
        try:
            # Carrega modelo de categoria
            category_model_path = os.path.join(self.model_dir, 'category_model.pkl')
            if os.path.exists(category_model_path):
                with open(category_model_path, 'rb') as f:
                    self.category_model = pickle.load(f)
                logger.info("Modelo de categoria carregado com sucesso")
            
            # Carrega modelo de prioridade
            priority_model_path = os.path.join(self.model_dir, 'priority_model.pkl')
            if os.path.exists(priority_model_path):
                with open(priority_model_path, 'rb') as f:
                    self.priority_model = pickle.load(f)
                logger.info("Modelo de prioridade carregado com sucesso")
            
            # Carrega modelo de departamento
            department_model_path = os.path.join(self.model_dir, 'department_model.pkl')
            if os.path.exists(department_model_path):
                with open(department_model_path, 'rb') as f:
                    self.department_model = pickle.load(f)
                logger.info("Modelo de departamento carregado com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao carregar modelos: {str(e)}")
            # Reseta modelos em caso de erro
            self.category_model = None
            self.priority_model = None
            self.department_model = None
    
    def _save_models(self) -> None:
        """Salva modelos treinados no disco."""
        try:
            # Salva modelo de categoria
            if self.category_model:
                category_model_path = os.path.join(self.model_dir, 'category_model.pkl')
                with open(category_model_path, 'wb') as f:
                    pickle.dump(self.category_model, f)
                logger.info("Modelo de categoria salvo com sucesso")
            
            # Salva modelo de prioridade
            if self.priority_model:
                priority_model_path = os.path.join(self.model_dir, 'priority_model.pkl')
                with open(priority_model_path, 'wb') as f:
                    pickle.dump(self.priority_model, f)
                logger.info("Modelo de prioridade salvo com sucesso")
            
            # Salva modelo de departamento
            if self.department_model:
                department_model_path = os.path.join(self.model_dir, 'department_model.pkl')
                with open(department_model_path, 'wb') as f:
                    pickle.dump(self.department_model, f)
                logger.info("Modelo de departamento salvo com sucesso")
        
        except Exception as e:
            logger.error(f"Erro ao salvar modelos: {str(e)}")
    
    def train(self, training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Treina os modelos de classificação.
        
        Args:
            training_data: Lista de e-mails rotulados para treinamento
            
        Returns:
            Dict[str, Any]: Métricas de desempenho dos modelos
        """
        if not training_data:
            logger.error("Dados de treinamento vazios")
            return {
                'category': {'accuracy': 0.0, 'report': {}},
                'priority': {'accuracy': 0.0, 'report': {}},
                'department': {'accuracy': 0.0, 'report': {}}
            }
        
        try:
            # Prepara dados para treinamento
            texts = []
            category_labels = []
            priority_labels = []
            department_labels = []
            
            for email in training_data:
                # Extrai texto
                text = self._extract_text_for_classification(email)
                texts.append(text)
                
                # Extrai rótulos
                category_labels.append(email.get('category', 'outro'))
                priority_labels.append(email.get('priority', 'normal'))
                department_labels.append(email.get('department', 'triagem'))
            
            # Treina modelo de categoria
            category_metrics = self._train_category_model(texts, category_labels)
            
            # Treina modelo de prioridade
            priority_metrics = self._train_priority_model(texts, priority_labels)
            
            # Treina modelo de departamento
            department_metrics = self._train_department_model(texts, department_labels)
            
            # Salva modelos
            self._save_models()
            
            return {
                'category': category_metrics,
                'priority': priority_metrics,
                'department': department_metrics
            }
        
        except Exception as e:
            logger.error(f"Erro ao treinar modelos: {str(e)}")
            return {
                'category': {'accuracy': 0.0, 'report': {}, 'error': str(e)},
                'priority': {'accuracy': 0.0, 'report': {}, 'error': str(e)},
                'department': {'accuracy': 0.0, 'report': {}, 'error': str(e)}
            }
    
    def _train_category_model(self, texts: List[str], labels: List[str]) -> Dict[str, Any]:
        """
        Treina o modelo de classificação de categoria.
        
        Args:
            texts: Lista de textos para treinamento
            labels: Lista de rótulos de categoria
            
        Returns:
            Dict[str, Any]: Métricas de desempenho do modelo
        """
        # Divide dados em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
        
        # Cria pipeline de classificação
        self.category_model = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ('clf', MultinomialNB())
        ])
        
        # Treina modelo
        self.category_model.fit(X_train, y_train)
        
        # Avalia modelo
        y_pred = self.category_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        logger.info(f"Modelo de categoria treinado com acurácia: {accuracy:.4f}")
        
        return {
            'accuracy': accuracy,
            'report': report
        }
    
    def _train_priority_model(self, texts: List[str], labels: List[str]) -> Dict[str, Any]:
        """
        Treina o modelo de classificação de prioridade.
        
        Args:
            texts: Lista de textos para treinamento
            labels: Lista de rótulos de prioridade
            
        Returns:
            Dict[str, Any]: Métricas de desempenho do modelo
        """
        # Divide dados em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
        
        # Cria pipeline de classificação
        self.priority_model = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ('clf', RandomForestClassifier(n_estimators=100, random_state=42))
        ])
        
        # Treina modelo
        self.priority_model.fit(X_train, y_train)
        
        # Avalia modelo
        y_pred = self.priority_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        logger.info(f"Modelo de prioridade treinado com acurácia: {accuracy:.4f}")
        
        return {
            'accuracy': accuracy,
            'report': report
        }
    
    def _train_department_model(self, texts: List[str], labels: List[str]) -> Dict[str, Any]:
        """
        Treina o modelo de classificação de departamento.
        
        Args:
            texts: Lista de textos para treinamento
            labels: Lista de rótulos de departamento
            
        Returns:
            Dict[str, Any]: Métricas de desempenho do modelo
        """
        # Divide dados em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, random_state=42
        )
        
        # Cria pipeline de classificação
        self.department_model = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
            ('clf', SVC(kernel='linear', probability=True, random_state=42))
        ])
        
        # Treina modelo
        self.department_model.fit(X_train, y_train)
        
        # Avalia modelo
        y_pred = self.department_model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        logger.info(f"Modelo de departamento treinado com acurácia: {accuracy:.4f}")
        
        return {
            'accuracy': accuracy,
            'report': report
        }
    
    def classify(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classifica um e-mail.
        
        Args:
            email: E-mail a ser classificado
            
        Returns:
            Dict[str, Any]: E-mail com classificações
        """
        try:
            # Cria cópia do e-mail para não modificar o original
            classified_email = email.copy()
            
            # Extrai texto para classificação
            text = self._extract_text_for_classification(email)
            
            # Classifica categoria
            if self.category_model:
                category, category_proba = self._classify_category(text)
                classified_email['ml_category'] = category
                classified_email['ml_category_confidence'] = category_proba
            else:
                # Usa categoria do parser se modelo não estiver disponível
                classified_email['ml_category'] = email.get('category', 'outro')
                classified_email['ml_category_confidence'] = email.get('category_confidence', 0.0)
            
            # Classifica prioridade
            if self.priority_model:
                priority, priority_proba = self._classify_priority(text)
                classified_email['ml_priority'] = priority
                classified_email['ml_priority_confidence'] = priority_proba
            else:
                # Usa prioridade do parser se modelo não estiver disponível
                classified_email['ml_priority'] = email.get('priority', 'normal')
                classified_email['ml_priority_confidence'] = 0.0
            
            # Classifica departamento
            if self.department_model:
                department, department_proba = self._classify_department(text)
                classified_email['department'] = department
                classified_email['department_confidence'] = department_proba
            else:
                # Determina departamento com base na categoria
                category = classified_email.get('ml_category', 'outro')
                department = self.category_to_department.get(category, 'triagem')
                classified_email['department'] = department
                classified_email['department_confidence'] = classified_email.get('ml_category_confidence', 0.0)
            
            # Combina classificações de ML com regras baseadas em entidades
            self._apply_entity_based_rules(classified_email)
            
            return classified_email
        
        except Exception as e:
            logger.error(f"Erro ao classificar e-mail: {str(e)}")
            # Retorna o e-mail original com classificações padrão
            email['ml_category'] = email.get('category', 'outro')
            email['ml_category_confidence'] = email.get('category_confidence', 0.0)
            email['ml_priority'] = email.get('priority', 'normal')
            email['ml_priority_confidence'] = 0.0
            email['department'] = self.category_to_department.get(email.get('category', 'outro'), 'triagem')
            email['department_confidence'] = 0.0
            email['classification_error'] = str(e)
            return email
    
    def _classify_category(self, text: str) -> Tuple[str, float]:
        """
        Classifica a categoria de um e-mail.
        
        Args:
            text: Texto do e-mail
            
        Returns:
            Tuple[str, float]: Categoria e confiança
        """
        # Prediz categoria
        category = self.category_model.predict([text])[0]
        
        # Obtém probabilidades
        probas = self.category_model.predict_proba([text])[0]
        
        # Obtém índice da categoria predita
        category_idx = list(self.category_model.classes_).index(category)
        
        # Obtém probabilidade da categoria predita
        category_proba = probas[category_idx]
        
        return category, float(category_proba)
    
    def _classify_priority(self, text: str) -> Tuple[str, float]:
        """
        Classifica a prioridade de um e-mail.
        
        Args:
            text: Texto do e-mail
            
        Returns:
            Tuple[str, float]: Prioridade e confiança
        """
        # Prediz prioridade
        priority = self.priority_model.predict([text])[0]
        
        # Obtém probabilidades
        probas = self.priority_model.predict_proba([text])[0]
        
        # Obtém índice da prioridade predita
        priority_idx = list(self.priority_model.classes_).index(priority)
        
        # Obtém probabilidade da prioridade predita
        priority_proba = probas[priority_idx]
        
        return priority, float(priority_proba)
    
    def _classify_department(self, text: str) -> Tuple[str, float]:
        """
        Classifica o departamento de um e-mail.
        
        Args:
            text: Texto do e-mail
            
        Returns:
            Tuple[str, float]: Departamento e confiança
        """
        # Prediz departamento
        department = self.department_model.predict([text])[0]
        
        # Obtém probabilidades
        probas = self.department_model.predict_proba([text])[0]
        
        # Obtém índice do departamento predito
        department_idx = list(self.department_model.classes_).index(department)
        
        # Obtém probabilidade do departamento predito
        department_proba = probas[department_idx]
        
        return department, float(department_proba)
    
    def _extract_text_for_classification(self, email: Dict[str, Any]) -> str:
        """
        Extrai texto de um e-mail para classificação.
        
        Args:
            email: E-mail
            
        Returns:
            str: Texto extraído
        """
        texts = []
        
        # Adiciona assunto (com peso maior)
        subject = email.get('subject', '')
        if subject:
            texts.append(subject)
            texts.append(subject)  # Duplica para dar mais peso
        
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
        
        # Adiciona texto de anexos processados
        if 'processed_attachments' in email:
            for attachment in email['processed_attachments']:
                attachment_text = attachment.get('text', '')
                if attachment_text:
                    # Limita o tamanho do texto do anexo
                    texts.append(attachment_text[:1000])
        
        # Combina todos os textos
        return "\n\n".join(texts)
    
    def _apply_entity_based_rules(self, email: Dict[str, Any]) -> None:
        """
        Aplica regras baseadas em entidades para refinar classificações.
        
        Args:
            email: E-mail classificado
        """
        entities = email.get('entities', {})
        
        # Regras para categoria
        if 'contract_number' in entities and 'value' in entities:
            if email['ml_category'] == 'outro' or email['ml_category_confidence'] < 0.7:
                email['ml_category'] = 'pagamento'
                email['ml_category_confidence'] = max(email['ml_category_confidence'], 0.8)
        
        # Regras para prioridade
        if 'deadline' in entities:
            for deadline in entities['deadline']:
                if 'urgente' in deadline.lower() or 'imediato' in deadline.lower():
                    email['ml_priority'] = 'urgente'
                    email['ml_priority_confidence'] = 0.9
                    break
        
        # Regras para departamento
        if email['ml_category'] == 'pagamento' and email['ml_category_confidence'] > 0.7:
            email['department'] = 'financeiro'
            email['department_confidence'] = 0.9
        elif 'contract_number' in entities and len(entities['contract_number']) > 0:
            if 'cancelamento' in email['ml_category'] or 'alteracao' in email['ml_category']:
                email['department'] = 'juridico'
                email['department_confidence'] = 0.85

# Exemplo de uso
if __name__ == "__main__":
    # Cria classificador
    classifier = EmailClassifier()
    
    # Exemplo de e-mail
    email = {
        'subject': 'Renovação de Contrato - Escola Municipal João da Silva',
        'body': '''
        Prezados,
        
        Solicito a renovação do contrato nº 12345 da Escola Municipal João da Silva.
        O contrato atual vence em 30/05/2023 e gostaríamos de renová-lo por mais 12 meses.
        
        O valor atual é de R$ 5.000,00 mensais.
        
        Atenciosamente,
        Maria Oliveira
        Diretora
        Tel: (11) 98765-4321
        ''',
        'entities': {
            'contract_numbers': ['12345'],
            'school_names': ['Escola Municipal João da Silva'],
            'dates': ['30/05/2023'],
            'value': ['R$ 5.000,00']
        },
        'category': 'renovacao',
        'category_confidence': 0.85,
        'priority': 'normal'
    }
    
    # Classifica e-mail
    classified_email = classifier.classify(email)
    
    # Exibe resultados
    print(f"Categoria (ML): {classified_email['ml_category']} (confiança: {classified_email['ml_category_confidence']:.2f})")
    print(f"Prioridade (ML): {classified_email['ml_priority']} (confiança: {classified_email['ml_priority_confidence']:.2f})")
    print(f"Departamento: {classified_email['department']} (confiança: {classified_email['department_confidence']:.2f})")
