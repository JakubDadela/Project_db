from pymongo import MongoClient

class MongoDBMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Kod inicjalizujący wykonywany przy ładowaniu middleware

    def __call__(self, request):
        # Przed przekazaniem żądania do widoku
        client = MongoClient('mongodb://localhost:27017/')
        request.db_client = client  # Przekazanie klienta bazy danych do obiektu żądania
        response = self.get_response(request)
        # Po przekazaniu żądania do widoku

        # Po przekazaniu odpowiedzi z widoku
        client.close()  # Zamknięcie połączenia z bazą danych
        return response