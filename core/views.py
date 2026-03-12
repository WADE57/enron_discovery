from django.shortcuts import render

# Create your views here.

#exple hello world
def hello_world(request):
    return render(request, 'hello_world.html', {'message': 'Hello, World!'})
