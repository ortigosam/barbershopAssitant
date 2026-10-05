from langchain_core.tools import tool

from agent.http_client import request


@tool
def get_client() -> dict:
    """Consulta la ficha del cliente autenticado.

    Selecciona esta tool cuando el usuario pregunte si tiene ficha, si está
    registrado o quiera consultar sus propios datos básicos.

    La identidad se obtiene del teléfono verificado del canal y no se recibe
    como argumento. Nunca pidas ni envíes un teléfono para elegir otra ficha.

    Esta es una operación de SOLO LECTURA: no crea ni modifica clientes.
    Si no existe una ficha, devuelve ``success=false`` con el código
    ``CLIENT_NOT_FOUND``. Si existe, devuelve ``success=true`` y sus datos.

    No la uses para:
    - crear una ficha (usa ``create_client``);
    - cambiar el nombre (usa ``update_client``);
    - listar todos los clientes, porque el usuario sólo puede consultar su
      propia ficha.
    """
    return request("GET", "/clients/me")


@tool
def create_client(name: str) -> dict:
    """Crea una ficha para el cliente autenticado.

    Selecciona esta tool cuando el usuario pida registrarse, crear su ficha o
    darse de alta, y haya proporcionado su nombre. El teléfono del cliente lo
    aporta la identidad verificada del canal; nunca lo extraigas del mensaje
    ni lo añadas como argumento.

    Parámetros:
    - ``name``: nombre que el usuario ha indicado explícitamente, limpio y no
      vacío. No inventes un nombre ni uses el teléfono como nombre.

    Esta es una operación de ESCRITURA. Sólo se ha creado la ficha si la
    respuesta contiene ``success=true``. Si la ficha ya existe, devuelve
    ``CLIENT_ALREADY_EXISTS``; en ese caso no afirmes que se ha creado y ofrece
    ``update_client`` si el usuario quería cambiar su nombre.

    No la uses para consultar si existe una ficha (usa ``get_client``) ni para
    cambiar un nombre existente (usa ``update_client``).
    """
    return request("POST", "/clients/me", json={"name": name})


@tool
def update_client(name: str) -> dict:
    """Actualiza el nombre de la ficha del cliente autenticado.

    Selecciona esta tool únicamente cuando el usuario quiera cambiar, corregir
    o actualizar su propio nombre y haya proporcionado el nuevo nombre de forma
    explícita. La identidad se toma del teléfono verificado del canal; no
    acepta ni cambia el teléfono.

    Parámetros:
    - ``name``: nuevo nombre indicado por el usuario. No conserves el nombre
      anterior si el usuario ha proporcionado uno nuevo y no inventes valores.

    Esta es una operación de ESCRITURA. No confirmes que el nombre se ha
    actualizado hasta recibir ``success=true``. Un fallo de la API significa
    que el cambio no está confirmado.

    No la uses para crear una ficha nueva (usa ``create_client``), comprobar si
    existe (usa ``get_client``) ni para modificar una reserva.
    """
    return request("PUT", "/clients/me", json={"name": name})
