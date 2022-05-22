from django.shortcuts import render
    
def home(request):
    if request.method == "GET":
            r = requests.get('http://api.embed.ly/1/oembed?key=' + settings.EMBEDLY_KEY + '&url=' + url)
            json = r.json()
            serializer = EmbedSerializer(data=json)
            if serializer.is_valid():
                embed = serializer.save()
                return render(request, 'embeds.html', {'embed': embed})
    else:
        form = SubmitEmbed()

    return render(request, 'home.html')

