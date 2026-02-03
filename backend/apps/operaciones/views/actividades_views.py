

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class ActividadesView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    # permission_classes = []
    
    def get(self, request):
        return Response({"message": "Actividades endpoint"})
    
    def post(self, request):
        return Response({"message": "Crear una nueva actividad"})