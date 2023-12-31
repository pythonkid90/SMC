# Stock Market Craziness

<p style="color:blue; font-size: 1.3rem">v0.2</p>

Play [here.](https://stock-game.onrender.com)

Stock market game made using Flask and Python.

## Running on your computer

1. If you haven't already, [download python.](https://www.python.org/downloads/)

2. Install requirements:

   ```bash
   pip install -r requirements.txt
   ```

3. Now, go to main.py and uncomment the last few lines - 

   ```python
   # if __name__ == '__main__':
       # app.run(debug=True)
   ```

   should become

   ```python
   if __name__ == '__main__':
       app.run(debug=True)
   ```

4. After that, you need to claim your api key from <https://alphavantage.co> and <https://polygon.io>.
   Alphavantage is mandatory, and Polygon is optional.
   I recommend to claim an api key from both as it gives you more api credits.

   Once you have it, you need to set it as an *environment variable.*
   Usually, you need to run

   ```bash
   export STOCK_API_KEY='[alphavantage api key]'
   ```
   
   and for Polygon - 

   ```bash
   export POLYGON_API_KEY='[polygon api key]'
   ```
   
   However, depending on your IDE (Code editor), you might 
   need to do something different. On PyCharm, navigate to 
   ***Run > Edit Configurations*** and set your variables there. R

5. The final thing you need to do is to type this in the terminal:

   ```bash
   python3 main.py
   ```

Navigate to <https://localhost:5000>,
and you should have the website running on your computer!

> When you type *`python3 main.py`* in the terminal, it might say to go to
> <https://127.0.0.1:5000> instead of <https://localhost:5000>.
> Both will work, as **`localhost`** is the same as **`127.0.0.1`**.

