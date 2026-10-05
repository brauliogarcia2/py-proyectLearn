import kivy
from kivy.app import App
from kivy.uix.label import Label

class FirstApp(kivy.app.App):

# Our class have to extend from the app class

def build(self):
    return Label(text ='hola el mundo es hermoso')

FirstApp().run()