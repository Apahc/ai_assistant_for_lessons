"""
Сервис для работы с Llama API
"""
import os
from typing import Optional
from huggingface_hub import InferenceClient
from config import HF_TOKEN, LLAMA_MODEL, LLAMA_PROVIDER
from prompts import (
    RAG_ANSWER_PROMPT,
    QUERY_REFINEMENT_PROMPT,
    KEYWORD_EXTRACTION_PROMPT,
    LESSONS_SUMMARY_PROMPT
)


class LLMService:
    """Сервис для взаимодействия с Llama API"""
    
    def __init__(self):
        self.api_key = HF_TOKEN
        self.model = LLAMA_MODEL
        self.provider = LLAMA_PROVIDER
        self.client = None
        
        if self.api_key:
            try:
                self.client = InferenceClient(
                    provider=self.provider,
                    token=self.api_key,
                )
            except Exception as e:
                print(f"Ошибка инициализации LLM клиента: {e}")
                self.client = None
    
    def _check_client(self) -> bool:
        """Проверка доступности клиента"""
        if not self.api_key:
            print("Переменная окружения hf_token не найдена.")
            return False
        if not self.client:
            print("LLM клиент не инициализирован.")
            return False
        return True
    
    def query_llama_api(self, prompt: str, stream: bool = False) -> Optional[str]:
        """
        Отправляет запрос к API модели Llama
        
        Args:
            prompt: Текст промпта
            stream: Использовать ли стриминг (пока не поддерживается)
            
        Returns:
            Ответ от модели или None в случае ошибки
        """
        if not self._check_client():
            return None
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                stream=stream,
            )
            
            if stream:
                # Для стриминга нужно будет обработать иначе
                return None
            
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Произошла ошибка при вызове API: {e}")
            return None
    
    def generate_rag_answer(
        self, 
        question: str, 
        context: str
    ) -> Optional[str]:
        """
        Генерирует ответ на основе контекста из RAG
        
        Args:
            question: Вопрос пользователя
            context: Контекст из базы знаний
            
        Returns:
            Сгенерированный ответ
        """
        prompt = RAG_ANSWER_PROMPT.format(
            context=context,
            question=question
        )
        return self.query_llama_api(prompt)
    
    def refine_query(self, query: str) -> Optional[str]:
        """
        Улучшает поисковый запрос пользователя
        
        Args:
            query: Исходный запрос
            
        Returns:
            Улучшенный запрос или исходный, если не удалось улучшить
        """
        prompt = QUERY_REFINEMENT_PROMPT.format(query=query)
        refined = self.query_llama_api(prompt)
        return refined if refined else query
    
    def extract_keywords(self, query: str) -> Optional[str]:
        """
        Извлекает ключевые слова из запроса
        
        Args:
            query: Поисковый запрос
            
        Returns:
            Список ключевых слов через запятую
        """
        prompt = KEYWORD_EXTRACTION_PROMPT.format(query=query)
        return self.query_llama_api(prompt)
    
    def summarize_lessons(self, lessons: str) -> Optional[str]:
        """
        Суммаризирует найденные уроки
        
        Args:
            lessons: Текст найденных уроков
            
        Returns:
            Резюме уроков
        """
        prompt = LESSONS_SUMMARY_PROMPT.format(lessons=lessons)
        return self.query_llama_api(prompt)
    
    def is_available(self) -> bool:
        """Проверка доступности сервиса"""
        return self._check_client()

