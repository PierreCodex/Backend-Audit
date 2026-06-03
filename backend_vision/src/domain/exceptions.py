"""Excepciones de dominio. Las capas externas las atrapan y traducen a HTTP."""


class DomainError(Exception):
    """Base de todos los errores de dominio."""


class CapturaInvalida(DomainError):
    """La captura recibida del ESP32 no cumple invariantes mínimos."""


class ConfianzaInsuficiente(DomainError):
    """Claude analizó pero su confianza está por debajo del umbral configurado."""


class POSNoDisponible(DomainError):
    """El POS Laravel no respondió o rechazó el request."""


class AnalizadorNoDisponible(DomainError):
    """La API de Claude falló (timeout, rate limit, error 5xx)."""