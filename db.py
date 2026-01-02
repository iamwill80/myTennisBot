import mysql.connector

conn = mysql.connector.connect(
    host="switchyard.proxy.rlwy.net",
    user="root",
    password="EtSYgitrneEBIPKZZYSgYiNYCIjeoFVo",
    database="railway",
    port=3306  # se specificato da Railway
)

c = conn.cursor()

