import streamlit as st
import psycopg2

# ---------------------- PostgreSQL Connection ----------------------
def connect_to_database():
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres.mvajileusmcjthjhndnh",
            password="Ketwonereid@1234",
            host="aws-0-us-east-1.pooler.supabase.com",
            port="6543",
            sslmode="require"
        )
        return conn
    except Exception as e:
        st.error("Error connecting to Supabase: " + str(e))
        return None

def fetch_all(cursor, query, params=None):
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except Exception as e:
        cursor.connection.rollback()  # rollback on error
        raise e

def execute_commit(cursor, conn, query, params=None):
    try:
        cursor.execute(query, params or ())
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e

# === Member Functions ===
def get_members(cursor):
    try:
        return fetch_all(cursor, "SELECT memberid, name, email, phonenumber FROM member ORDER BY memberid")
    except Exception as e:
        st.error(f"Error fetching members: {e}")
        return []

def add_member(cursor, conn, name, email, phone):
    execute_commit(cursor, conn, 
        "INSERT INTO member (name, email, phonenumber) VALUES (%s, %s, %s)",
        (name, email, phone)
    )

def delete_member(cursor, conn, member_id):
    execute_commit(cursor, conn, "DELETE FROM member WHERE memberid = %s", (member_id,))

# === Book Functions ===
def get_books(cursor):
    try:
        return fetch_all(cursor, "SELECT bookid, title, author, copiesavailable FROM book ORDER BY bookid")
    except Exception as e:
        st.error(f"Error fetching books: {e}")
        return []

def add_book(cursor, conn, title, author, copies):
    execute_commit(cursor, conn,
        "INSERT INTO book (title, author, copiesavailable) VALUES (%s, %s, %s)",
        (title, author, copies)
    )

def update_book_copies(cursor, conn, book_id, copies):
    execute_commit(cursor, conn,
        "UPDATE book SET copiesavailable = %s WHERE bookid = %s",
        (copies, book_id)
    )

# === Borrow/Return Functions ===
def borrow_book(cursor, conn, member_id, book_id, loan_date, due_date):
    try:
        cursor.execute('CALL "BorrowBook"(%s, %s, %s::date, %s::date)', (member_id, book_id, loan_date, due_date))
        conn.commit()
        st.success("Book borrowed successfully.")
    except Exception as e:
        conn.rollback()
        st.error(f"Error calling BorrowBook procedure: {e}")

def return_book(cursor, conn, borrow_id, return_date):
    try:
        cursor.execute('CALL "ReturnBook"(%s, %s::date)', (borrow_id, return_date))
        conn.commit()
        st.success("Book returned successfully.")
    except Exception as e:
        conn.rollback()
        st.error(f"Error calling ReturnBook procedure: {e}")

# === Fine Functions ===
def pay_fine(cursor, conn, fine_id):
    try:
        execute_commit(cursor, conn, "UPDATE fine SET paid = 'Yes' WHERE fineid = %s", (fine_id,))
        st.success("Fine paid successfully.")
    except Exception as e:
        st.error(f"Error paying fine: {e}")

def get_all_fines(cursor):
    try:
        query = """
            SELECT f.fineid, f.borrowid, f.amount, f.paid, b.memberid, m.name
            FROM fine f
            JOIN borrow b ON f.borrowid = b.borrowid
            JOIN member m ON b.memberid = m.memberid
            ORDER BY f.fineid
        """
        return fetch_all(cursor, query)
    except Exception as e:
        st.error(f"Error fetching fines: {e}")
        return []

def search_unpaid_fines(cursor, member_id):
    try:
        query = """
            SELECT f.fineid, f.borrowid, f.amount, f.paid
            FROM fine f
            JOIN borrow b ON f.borrowid = b.borrowid
            WHERE b.memberid = %s AND f.paid = 'No'
        """
        return fetch_all(cursor, query, (member_id,))
    except Exception as e:
        st.error(f"Error searching unpaid fines: {e}")
        return []

def get_fine_audit_history(cursor):
    try:
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='fineaudit' ORDER BY ordinal_position")
        columns = [row[0] for row in cursor.fetchall()]
        if not columns:
            return [], []
        query = f"SELECT {', '.join(columns)} FROM fineaudit ORDER BY timestamp DESC"
        data = fetch_all(cursor, query)
        return columns, data
    except Exception as e:
        st.error(f"Error fetching fine audit history: {e}")
        return [], []

# === Streamlit App ===
def main():
    st.title("Library Management System - Supabase")

    conn = connect_to_database()
    if not conn:
        st.stop()
    cursor = conn.cursor()

    # --- Members ---
    st.header("Manage Members")
    with st.expander("Add Member"):
        name = st.text_input("Name", key="member_name")
        email = st.text_input("Email", key="member_email")
        phone = st.text_input("Phone", key="member_phone")
        if st.button("Add Member"):
            if name and email and phone:
                try:
                    add_member(cursor, conn, name, email, phone)
                    st.success("Member added successfully!")
                except Exception as e:
                    st.error(f"Error adding member: {e}")
            else:
                st.error("Please fill all member fields.")

    with st.expander("Delete Member"):
        del_member_id = st.text_input("Member ID to delete", key="del_member")
        if st.button("Delete Member"):
            if del_member_id.isdigit():
                try:
                    delete_member(cursor, conn, int(del_member_id))
                    st.success("Member deleted if existed.")
                except Exception as e:
                    st.error(f"Error deleting member: {e}")
            else:
                st.error("Enter a valid numeric Member ID.")

    st.subheader("Members List")
    members = get_members(cursor)
    st.table(members)

    # --- Books ---
    st.header("Manage Books")
    with st.expander("Add Book"):
        title = st.text_input("Title", key="book_title")
        author = st.text_input("Author", key="book_author")
        copies = st.text_input("Copies Available", key="book_copies")
        if st.button("Add Book"):
            if title and author:
                if copies.isdigit() or copies == "":
                    try:
                        add_book(cursor, conn, title, author, int(copies) if copies else 0)
                        st.success("Book added successfully!")
                    except Exception as e:
                        st.error(f"Error adding book: {e}")
                else:
                    st.error("Copies must be a number.")
            else:
                st.error("Title and Author are required.")

    with st.expander("Update Book Copies"):
        upd_book_id = st.text_input("Book ID", key="upd_book_id")
        upd_copies = st.text_input("New Copies", key="upd_copies")
        if st.button("Update Copies"):
            if upd_book_id.isdigit() and upd_copies.isdigit():
                try:
                    update_book_copies(cursor, conn, int(upd_book_id), int(upd_copies))
                    st.success("Copies updated successfully!")
                except Exception as e:
                    st.error(f"Error updating copies: {e}")
            else:
                st.error("Book ID and Copies must be numeric.")

    st.subheader("Books List")
    books = get_books(cursor)
    st.table(books)

    # --- Borrow/Return ---
    st.header("Borrow/Return Books")
    with st.expander("Borrow Book"):
        mem_id = st.text_input("Member ID", key="borrow_mem_id")
        book_id = st.text_input("Book ID", key="borrow_book_id")
        loan_date = st.text_input("Loan Date (YYYY-MM-DD)", key="loan_date")
        due_date = st.text_input("Due Date (YYYY-MM-DD)", key="due_date")
        if st.button("Borrow Book"):
            if mem_id.isdigit() and book_id.isdigit() and loan_date and due_date:
                borrow_book(cursor, conn, int(mem_id), int(book_id), loan_date, due_date)
            else:
                st.error("Please enter valid numeric Member ID, Book ID and valid dates.")

    with st.expander("Return Book"):
        borrow_id = st.text_input("Borrow ID", key="return_borrow_id")
        return_date = st.text_input("Return Date (YYYY-MM-DD)", key="return_date")
        if st.button("Return Book"):
            if borrow_id.isdigit() and return_date:
                return_book(cursor, conn, int(borrow_id), return_date)
            else:
                st.error("Please enter a valid Borrow ID and Return Date.")

    # --- Fines ---
    st.header("Fines Management")
    with st.expander("Pay Fine"):
        fine_id = st.text_input("Fine ID to pay", key="pay_fine_id")
        if st.button("Pay Fine"):
            if fine_id.isdigit():
                pay_fine(cursor, conn, int(fine_id))
            else:
                st.error("Please enter a valid numeric Fine ID.")

    st.subheader("All Fines")
    fines = get_all_fines(cursor)
    st.table(fines)

    with st.expander("Search Unpaid Fines by Member ID"):
        search_mem_id = st.text_input("Member ID", key="search_unpaid_member")
        if st.button("Search Unpaid Fines"):
            if search_mem_id.isdigit():
                unpaid = search_unpaid_fines(cursor, int(search_mem_id))
                st.table(unpaid)
            else:
                st.error("Please enter a valid numeric Member ID.")

    st.subheader("Fine Audit History")
    columns, audit_data = get_fine_audit_history(cursor)
    if audit_data:
        st.dataframe(audit_data, column_order=columns)
    else:
        st.write("No fine audit history available.")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()

