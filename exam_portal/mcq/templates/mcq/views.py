from django.shortcuts import render

def upload_mcq(request):
    context = {}
    return render(request, "mcq/upload.html", context)  # mcq/ is important
