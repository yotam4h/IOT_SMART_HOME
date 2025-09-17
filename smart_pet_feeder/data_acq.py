# data acquisition module

import pandas as pd
from .config import *
import sqlite3
from sqlite3 import Error
from datetime import datetime
import logging
from .config import logs_dir

logger = logging.getLogger(__name__)
_fh = logging.FileHandler(str(logs_dir / 'data_acq.log'))
_fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s | %(message)s'))
logger.addHandler(_fh)

def create_connection(db_file=db_name):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        pp = ('Connected to version: '+ sqlite3.version)
        logger.debug(pp)
        return conn
    except Error as e:
        logger.exception(e)

    return conn


def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        logger.exception(e)


def init_db(database):
    table_stmt = """
        CREATE TABLE IF NOT EXISTS `data` (
            `name`	TEXT NOT NULL,
            `timestamp`	TEXT NOT NULL,
            `value`	TEXT NOT NULL
        );
    """
    conn = create_connection(database)
    if conn is not None:
        try:
            create_table(conn, table_stmt)
        finally:
            conn.close()
    else:
        logger.error("Error! cannot create the database connection.")

def timestamp():
    return str(datetime.fromtimestamp(datetime.timestamp(datetime.now()))).split('.')[0]
    

def add_IOT_data(name, updated, value):
    """
    Add new IOT device data into the data table
    :param conn:
    :param :
    :return: last row id
    """
    sql = ''' INSERT INTO data(name, timestamp, value)
              VALUES(?,?,?) '''
    conn = create_connection()
    if conn is not None:
        cur = conn.cursor()
        cur.execute(sql, [name, updated, value])
        conn.commit()
        re = cur.lastrowid
        conn.close()
        return re
    else:
        logger.error("Error! cannot create the database connection.")

def fetch_table_data_into_df(table_name, conn, name_filter):
    if table_name != "data":
        raise ValueError("Invalid table name")
    return pd.read_sql_query(
        f"SELECT * FROM {table_name} WHERE name LIKE ?",
        conn,
        params=(name_filter,),
    )

def filter_by_date(table_name, start_date, end_date, meter):
    conn = create_connection()
    if conn is not None:
        if table_name != "data":
            raise ValueError("Invalid table name")
        cur = conn.cursor()                
        cur.execute(
            f"SELECT * FROM {table_name} WHERE name LIKE ? AND timestamp BETWEEN ? AND ?",
            (meter, start_date, end_date),
        )
        rows = cur.fetchall()   
        return rows
    else:
        logger.error("Error! cannot create the database connection.")     

def fetch_data(database,table_name, filter):
    TABLE_NAME = table_name    
    conn = create_connection(database)
    with conn:        
        return fetch_table_data_into_df(TABLE_NAME, conn, filter)
