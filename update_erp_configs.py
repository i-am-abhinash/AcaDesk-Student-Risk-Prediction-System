import mysql.connector

conn = mysql.connector.connect(user='root', password='Abhinash@19', host='127.0.0.1', database='acadesk_central')
cursor = conn.cursor()
cursor.execute("UPDATE erp_configs SET col_email='student_email', col_parent_email='parent_email' WHERE college_name='Vishnu'")
conn.commit()
print("Updated successfully")
