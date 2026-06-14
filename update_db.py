import mysql.connector
conn = mysql.connector.connect(host='localhost', user='root', password='Abhinash@19', database='acadesk_central', port=3306)
cursor = conn.cursor()
cursor.execute("UPDATE erp_configs SET col_branch_join = 'department_id', col_year = 'year_id' WHERE config_id = 1")
conn.commit()
conn.close()
