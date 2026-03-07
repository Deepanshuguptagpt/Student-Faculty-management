try:
    from backend.student import urls
    print('imported')
    print(dir(urls))
    if hasattr(urls, 'urlpatterns'):
        print('has urlpatterns')
    else:
        print('no urlpatterns')
except Exception as e:
    print(e)