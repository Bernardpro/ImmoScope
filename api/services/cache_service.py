import json
import logging
import os
from datetime import timedelta
from typing import Optional, Any

import redis

logger = logging.getLogger("redis_service")


class RedisConfig:
    """Configuration Redis avec variables d'environnement"""

    HOST = os.getenv("REDIS_HOST", "localhost")
    PORT = int(os.getenv("REDIS_PORT", 6379))
    DB = int(os.getenv("REDIS_DB", 0))
    TTL = timedelta(hours=int(os.getenv("REDIS_TTL_HOURS", 24)))
    PASSWORD = os.getenv("REDIS_PASSWORD", None)
    SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", 5))
    RETRY_ON_TIMEOUT = bool(os.getenv("REDIS_RETRY_ON_TIMEOUT", True))
    MAX_RETRIES = int(os.getenv("REDIS_MAX_RETRIES", 3))


class RedisError(Exception):
    """Exception personnalisée pour les erreurs Redis"""

    pass


class CacheService:
    """Service de gestion du cache Redis avec gestion d'erreurs améliorée"""

    def __init__(self):
        """Initialise la connexion Redis avec retry"""
        self._redis = None
        self._init_redis_connection()

    def _init_redis_connection(self) -> None:
        """Initialise la connexion Redis avec les paramètres de configuration"""
        try:
            self._redis = redis.Redis(
                host=RedisConfig.HOST,
                port=RedisConfig.PORT,
                db=RedisConfig.DB,
                password=RedisConfig.PASSWORD,
                socket_timeout=RedisConfig.SOCKET_TIMEOUT,
                retry_on_timeout=RedisConfig.RETRY_ON_TIMEOUT,
                decode_responses=True,
            )
            # Test de la connexion
            self._redis.ping()
            logger.info(f"Connected to Redis at {RedisConfig.HOST}:{RedisConfig.PORT}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise RedisError(f"Redis connection failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error initializing Redis: {str(e)}")
            raise

    def _ensure_connection(self) -> None:
        """Vérifie et rétablit la connexion si nécessaire"""
        if not self._redis:
            self._init_redis_connection()
        try:
            self._redis.ping()
        except:
            self._init_redis_connection()

    async def get_cache(self, key: str) -> Optional[Any]:
        """
        Récupère les données du cache

        Args:
            key: Clé de cache

        Returns:
            Optional[Any]: Données du cache ou None si non trouvé
        """
        try:
            self._ensure_connection()
            data = self._redis.get(key)
            if data:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(data)
            logger.debug(f"Cache miss for key: {key}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for key {key}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving cache for key {key}: {str(e)}")
            return None

    async def set_cache(
            self, key: str, data: Any, ttl: Optional[timedelta] = None
    ) -> bool:
        """
        Stocke les données dans le cache

        Args:
            key: Clé de cache
            data: Données à stocker
            ttl: Durée de vie optionnelle (utilise la config par défaut si non spécifié)

        Returns:
            bool: True si succès, False sinon
        """
        try:
            self._ensure_connection()
            json_data = json.dumps(data)
            expiry = (
                int(ttl.total_seconds())
                if ttl
                else int(RedisConfig.TTL.total_seconds())
            )

            self._redis.setex(key, expiry, json_data)
            logger.debug(f"Successfully cached data for key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {str(e)}")
            return False

    async def clear_cache(self, pattern: str = None) -> bool:
        """
        Vide le cache Redis

        Args:
            pattern: Pattern optional pour supprimer des clés spécifiques

        Returns:
            bool: True si succès, False sinon
        """
        try:
            self._ensure_connection()
            if pattern:
                keys = self._redis.keys(pattern)
                if keys:
                    self._redis.delete(*keys)
                logger.info(f"Cleared cache for pattern: {pattern}")
            else:
                self._redis.flushdb()
                logger.info("Cleared all cache")
            return True
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return False

    async def delete_key(self, key: str) -> bool:
        """
        Supprime une clé spécifique du cache

        Args:
            key: Clé à supprimer

        Returns:
            bool: True si succès, False sinon
        """
        try:
            self._ensure_connection()
            self._redis.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting key {key}: {str(e)}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Récupère le TTL restant d'une clé

        Args:
            key: Clé à vérifier

        Returns:
            Optional[int]: TTL en secondes ou None si la clé n'existe pas
        """
        try:
            self._ensure_connection()
            return self._redis.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {str(e)}")
            return None
