from django.db.models import Count
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.response import Response

from .models import Server
from .schema import server_list_docs
from .serializer import ServerSerializer


class ServerListViewSet(viewsets.ViewSet):
    queryset = Server.objects.all()
    
    @server_list_docs
    def list(self, request):
        """Lista servidores com opções de filtragem.
        
        Args:
            request (Request): Um objeto de solicitação HTTP contendo parâmetros de consulta.

        Returns:
            Response: Uma resposta HTTP contendo a lista de servidores serializados.

        Raises:
            AuthenticationFailed: Se a autenticação do usuário falhar ao filtrar por usuário ou serverid.
            ValidationError: Se ocorrerem erros de validação ao filtrar por serverid.

        Esta visualização permite listar servidores com opções de filtragem com base em vários parâmetros de consulta:
        - `category`: Filtra servidores pelo nome da categoria.
        - `qty`: Limita o número de servidores no resultado.
        - `by_user`: Filtra servidores pelo usuário autenticado (booleano: "true" ou "false").
        - `by_serverid`: Filtra servidores por um ID de servidor específico.
        - `num_members`: Inclui o número de membros no servidor (booleano: "true" ou "false").

        Se `by_user` ou `by_serverid` for especificado e o usuário não estiver autenticado, uma exceção AuthenticationFailed
        será lançada. Se estiver filtrando por `by_serverid`, uma exceção ValidationError será lançada se o ID do servidor
        fornecido for inválido ou não encontrado.

        Os resultados são serializados usando a classe ServerSerializer, e o número de membros é incluído
        no contexto de serialização se `num_members` estiver definido como "true"."""
        category = request.query_params.get("category")
        qty = request.query_params.get("qty")
        by_user = request.query_params.get("by_user") == "true"
        by_serverid = request.query_params.get("by_serverid")
        with_num_members = request.query_params.get("num_members") == "true"

        if category:
            self.queryset = self.queryset.filter(category__name=category)
        
        if by_user:
            if by_user and by_serverid and request.user.is_authenticated:
                user_id = request.user.id
                self.queryset = self.queryset.filter(member=user_id)
            else:
                raise AuthenticationFailed()
            
        if with_num_members:
            self.queryset = self.queryset.annotate(num_members=Count("member"))
        
        if by_serverid:
            if not request.user.is_authenticated:
                raise AuthenticationFailed()
            try:
                self.queryset = self.queryset.filter(id=by_serverid)
                if not self.queryset.exists():
                    raise ValidationError(detail=f"Server with id {by_serverid} not found")
            except ValueError:
                raise ValidationError(detail="Server value error")
        
        if qty:
            self.queryset = self.queryset[: int(qty)]

        serializer = ServerSerializer(self.queryset, many=True, context={"num_members": with_num_members})
        return Response(serializer.data)

