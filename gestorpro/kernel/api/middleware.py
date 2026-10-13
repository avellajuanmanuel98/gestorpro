class NoStoreApiMiddleware:
    """
    Las respuestas de la API traen datos del negocio y de sesión: ni el navegador
    ni un proxy intermedio deben guardarlas (OWASP ASVS 8.2.1). Una vista puede
    fijar su propia política de caché si lo necesita.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith('/api/') and 'Cache-Control' not in response:
            response['Cache-Control'] = 'no-store'
        return response
