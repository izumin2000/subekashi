import requests
from django.test import TestCase
from django.urls import reverse

class SongPageTest(TestCase) :
    def test_access_song_pages(self):
        api_url = 'https://lyrics.imicomweb.com/api/song/'
        response = requests.get(api_url)

        self.assertEqual(response.status_code, 200)

        songs = response.json()

        for song in songs:
            url = reverse('subekashi:song', args=[song['id']]) 
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            print(f"test {url} ({song['title']}) OK")
