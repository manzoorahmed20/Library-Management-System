
import streamlit as st
import sqlite3
import datetime

# -----------------------------------
# Database Settings
# -----------------------------------

DB_NAME = "library.db"
LOAN_DAYS = 14
FINE_PER_DAY = 50


def get_connection():
    return sqlite3.connect(DB_NAME)


def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE,
            quantity INTEGER NOT NULL DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            member_type TEXT NOT NULL,
            phone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issued_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (book_id) REFERENCES books(id),
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)

    conn.commit()
    conn.close()


# -----------------------------------
# Dashboard
# -----------------------------------

def show_dashboard():
    st.header("📊 Library Dashboard")

    conn = get_connection()

    total_books = conn.execute("""
        SELECT COALESCE(SUM(quantity), 0)
        FROM books
    """).fetchone()[0]

    total_titles = conn.execute("""
        SELECT COUNT(*)
        FROM books
    """).fetchone()[0]

    total_members = conn.execute("""
        SELECT COUNT(*)
        FROM members
    """).fetchone()[0]

    currently_issued = conn.execute("""
        SELECT COUNT(*)
        FROM issued_books
        WHERE return_date IS NULL
    """).fetchone()[0]

    overdue_count = conn.execute("""
        SELECT COUNT(*)
        FROM issued_books
        WHERE return_date IS NULL
        AND due_date < ?
    """, (datetime.date.today().isoformat(),)).fetchone()[0]

    conn.close()

    col1, col2, col3 = st.columns(3)
    col1.metric("📚 Available Copies", total_books)
    col2.metric("📖 Book Titles", total_titles)
    col3.metric("👥 Members", total_members)

    col4, col5 = st.columns(2)
    col4.metric("📤 Currently Issued", currently_issued)
    col5.metric("⚠️ Overdue Books", overdue_count)


# -----------------------------------
# Add Book
# -----------------------------------

def show_add_book():
    st.header("➕ Add a New Book")

    with st.form("add_book_form"):
        title = st.text_input("Book Title")
        author = st.text_input("Author")
        isbn = st.text_input("ISBN (optional)")
        quantity = st.number_input(
            "Quantity", min_value=1, step=1, value=1
        )

        submit = st.form_submit_button("Add Book")

    if submit:
        if not title.strip() or not author.strip():
            st.warning("Please enter the book title and author.")
            return

        conn = get_connection()

        try:
            conn.execute("""
                INSERT INTO books (title, author, isbn, quantity)
                VALUES (?, ?, ?, ?)
            """, (
                title.strip(),
                author.strip(),
                isbn.strip() or None,
                int(quantity)
            ))

            conn.commit()
            st.success("Book added successfully!")

        except sqlite3.IntegrityError:
            st.error(
                "This ISBN already exists. Please use a different ISBN."
            )

        finally:
            conn.close()


# -----------------------------------
# View All Books
# -----------------------------------

def show_all_books():
    st.header("📖 All Books")

    conn = get_connection()

    books = conn.execute("""
        SELECT id, title, author, isbn, quantity
        FROM books
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    if books:
        st.dataframe([
            {
                "Book ID": book[0],
                "Title": book[1],
                "Author": book[2],
                "ISBN": book[3] or "N/A",
                "Quantity": book[4]
            }
            for book in books
        ], use_container_width=True, hide_index=True)

    else:
        st.info("No books available yet.")


# -----------------------------------
# Search Books
# -----------------------------------

def show_search_books():
    st.header("🔍 Search Books")

    search_text = st.text_input(
        "Enter book title or author name"
    )

    if not search_text.strip():
        st.info("Enter a title or author name to search.")
        return

    search_term = f"%{search_text.strip()}%"

    conn = get_connection()

    results = conn.execute("""
        SELECT id, title, author, isbn, quantity
        FROM books
        WHERE title LIKE ? OR author LIKE ?
        ORDER BY title
    """, (search_term, search_term)).fetchall()

    conn.close()

    if results:
        st.success(f"{len(results)} book record(s) found.")

        st.dataframe([
            {
                "Book ID": book[0],
                "Title": book[1],
                "Author": book[2],
                "ISBN": book[3] or "N/A",
                "Quantity": book[4]
            }
            for book in results
        ], use_container_width=True, hide_index=True)

    else:
        st.warning("No matching books found.")


# -----------------------------------
# Register Member
# -----------------------------------

def show_register_member():
    st.header("👤 Register a New Member")

    with st.form("member_form"):
        name = st.text_input("Member Name")

        member_type = st.selectbox(
            "Member Type",
            ["Student", "Teacher"]
        )

        phone = st.text_input("Phone Number")

        register = st.form_submit_button("Register Member")

    if register:
        if not name.strip():
            st.warning("Please enter the member name.")
            return

        conn = get_connection()

        try:
            conn.execute("""
                INSERT INTO members (name, member_type, phone)
                VALUES (?, ?, ?)
            """, (
                name.strip(),
                member_type,
                phone.strip() or None
            ))

            conn.commit()
            st.success(f"{name.strip()} registered successfully!")

        finally:
            conn.close()


# -----------------------------------
# View All Members
# -----------------------------------

def show_all_members():
    st.header("👥 Registered Members")

    conn = get_connection()

    members = conn.execute("""
        SELECT id, name, member_type, phone
        FROM members
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    if members:
        st.dataframe([
            {
                "Member ID": member[0],
                "Name": member[1],
                "Member Type": member[2],
                "Phone": member[3] or "N/A"
            }
            for member in members
        ], use_container_width=True, hide_index=True)

    else:
        st.info("No members registered yet.")


# -----------------------------------
# Issue a Book
# -----------------------------------

def show_issue_book():
    st.header("📤 Issue a Book")

    conn = get_connection()

    books = conn.execute("""
        SELECT id, title, quantity
        FROM books
        WHERE quantity > 0
        ORDER BY title
    """).fetchall()

    members = conn.execute("""
        SELECT id, name, member_type
        FROM members
        ORDER BY name
    """).fetchall()

    conn.close()

    if not books:
        st.warning("No books are currently available to issue.")
        return

    if not members:
        st.warning("Please register a member before issuing a book.")
        return

    book_options = {
        f"{book[1]} (Available: {book[2]})": book[0]
        for book in books
    }

    member_options = {
        f"{member[1]} ({member[2]}) - ID: {member[0]}":
            (member[0], member[2])
        for member in members
    }

    with st.form("issue_book_form"):
        selected_book = st.selectbox(
            "Select Book",
            list(book_options.keys())
        )

        selected_member = st.selectbox(
            "Select Member",
            list(member_options.keys())
        )

        issue_button = st.form_submit_button("Issue Book")

    if not issue_button:
        return

    book_id = book_options[selected_book]
    member_id, member_type = member_options[selected_member]

    borrowing_limit = 3 if member_type == "Student" else 5

    conn = get_connection()

    try:
        cursor = conn.cursor()

        issued_count = cursor.execute("""
            SELECT COUNT(*)
            FROM issued_books
            WHERE member_id = ?
            AND return_date IS NULL
        """, (member_id,)).fetchone()[0]

        available_quantity = cursor.execute("""
            SELECT quantity
            FROM books
            WHERE id = ?
        """, (book_id,)).fetchone()

        if issued_count >= borrowing_limit:
            st.error(
                f"{member_type} borrowing limit is "
                f"{borrowing_limit} books."
            )
            return

        if available_quantity is None or available_quantity[0] <= 0:
            st.error("This book is no longer available.")
            return

        today = datetime.date.today()
        due_date = today + datetime.timedelta(days=LOAN_DAYS)

        cursor.execute("""
            INSERT INTO issued_books
            (book_id, member_id, issue_date, due_date)
            VALUES (?, ?, ?, ?)
        """, (
            book_id,
            member_id,
            today.isoformat(),
            due_date.isoformat()
        ))

        cursor.execute("""
            UPDATE books
            SET quantity = quantity - 1
            WHERE id = ?
        """, (book_id,))

        conn.commit()

        st.success(
            f"Book issued successfully! Due date: {due_date}"
        )

    finally:
        conn.close()


# -----------------------------------
# View Issued Books
# -----------------------------------

def show_issued_books():
    st.header("📋 Issued Books")

    conn = get_connection()

    issued_books = conn.execute("""
        SELECT
            issued_books.id,
            books.title,
            members.name,
            members.member_type,
            issued_books.issue_date,
            issued_books.due_date
        FROM issued_books
        JOIN books ON issued_books.book_id = books.id
        JOIN members ON issued_books.member_id = members.id
        WHERE issued_books.return_date IS NULL
        ORDER BY issued_books.due_date
    """).fetchall()

    conn.close()

    if issued_books:
        st.dataframe([
            {
                "Issue ID": book[0],
                "Book Title": book[1],
                "Member Name": book[2],
                "Member Type": book[3],
                "Issue Date": book[4],
                "Due Date": book[5]
            }
            for book in issued_books
        ], use_container_width=True, hide_index=True)

    else:
        st.info("No books are currently issued.")


# -----------------------------------
# Return Book
# -----------------------------------

def show_return_book():
    st.header("📥 Return a Book")

    conn = get_connection()

    issued_books = conn.execute("""
        SELECT
            issued_books.id,
            books.title,
            members.name,
            issued_books.due_date
        FROM issued_books
        JOIN books ON issued_books.book_id = books.id
        JOIN members ON issued_books.member_id = members.id
        WHERE issued_books.return_date IS NULL
        ORDER BY issued_books.due_date
    """).fetchall()

    conn.close()

    if not issued_books:
        st.info("There are no books waiting to be returned.")
        return

    issue_options = {
        f"ID: {book[0]} | {book[1]} | {book[2]} | Due: {book[3]}":
            book[0]
        for book in issued_books
    }

    with st.form("return_book_form"):
        selected_issue = st.selectbox(
            "Select the book to return",
            list(issue_options.keys())
        )

        return_button = st.form_submit_button("Return Book")

    if not return_button:
        return

    issue_id = issue_options[selected_issue]
    conn = get_connection()

    try:
        cursor = conn.cursor()

        record = cursor.execute("""
            SELECT book_id, due_date
            FROM issued_books
            WHERE id = ?
            AND return_date IS NULL
        """, (issue_id,)).fetchone()

        if not record:
            st.error("This book has already been returned.")
            return

        book_id, due_date_text = record

        today = datetime.date.today()
        due_date = datetime.date.fromisoformat(due_date_text)

        late_days = max((today - due_date).days, 0)
        fine = late_days * FINE_PER_DAY

        cursor.execute("""
            UPDATE issued_books
            SET return_date = ?
            WHERE id = ?
        """, (today.isoformat(), issue_id))

        cursor.execute("""
            UPDATE books
            SET quantity = quantity + 1
            WHERE id = ?
        """, (book_id,))

        conn.commit()

        st.success("Book returned successfully!")

        if fine > 0:
            st.warning(
                f"Late by {late_days} day(s). Fine: Rs. {fine}"
            )
        else:
            st.info("No fine! The book was returned on time.")

    finally:
        conn.close()


# -----------------------------------
# Overdue Books Report
# -----------------------------------

def show_overdue_books():
    st.header("⚠️ Overdue Books")

    today = datetime.date.today()

    conn = get_connection()

    overdue_books = conn.execute("""
        SELECT
            books.title,
            members.name,
            members.member_type,
            issued_books.due_date
        FROM issued_books
        JOIN books ON issued_books.book_id = books.id
        JOIN members ON issued_books.member_id = members.id
        WHERE issued_books.return_date IS NULL
        AND issued_books.due_date < ?
        ORDER BY issued_books.due_date
    """, (today.isoformat(),)).fetchall()

    conn.close()

    if not overdue_books:
        st.success("Great! No books are currently overdue.")
        return

    overdue_data = []
    total_fine = 0

    for book in overdue_books:
        due_date = datetime.date.fromisoformat(book[3])
        late_days = (today - due_date).days
        fine = late_days * FINE_PER_DAY

        total_fine += fine

        overdue_data.append({
            "Book Title": book[0],
            "Member Name": book[1],
            "Member Type": book[2],
            "Due Date": book[3],
            "Late Days": late_days,
            "Estimated Fine (Rs.)": fine
        })

    st.dataframe(
        overdue_data,
        use_container_width=True,
        hide_index=True
    )

    st.metric("Total Estimated Fine", f"Rs. {total_fine}")


# -----------------------------------
# Main Application and Navigation
# -----------------------------------


def show_delete_book():
    st.subheader("Delete Book")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, author, isbn, quantity
        FROM books
        ORDER BY title
    """)
    books = cursor.fetchall()
    conn.close()

    if not books:
        st.info("No books available to delete.")
        return

    book_options = {
        f"{book[1]} by {book[2]} (ISBN: {book[3]})": book[0]
        for book in books
    }

    selected_book = st.selectbox(
        "Select a book to delete",
        options=list(book_options.keys())
    )

    st.warning(
        "Deleting a book will also remove its issue history."
    )

    confirm = st.checkbox(
        "I confirm that I want to delete this book and its history."
    )

    if st.button("Delete Book", type="primary"):
        if not confirm:
            st.error("Please confirm before deleting.")
            return

        book_id = book_options[selected_book]

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                DELETE FROM issued_books
                WHERE book_id = ?
            """, (book_id,))

            cursor.execute("""
                DELETE FROM books
                WHERE id = ?
            """, (book_id,))

            conn.commit()
            st.success("Book and its issue history deleted successfully!")
            st.rerun()

        except sqlite3.Error as error:
            conn.rollback()
            st.error(f"Database error: {error}")

        finally:
            conn.close()


def main():

    
    st.set_page_config(
        page_title="Library Management System",
        page_icon="📚",
        layout="wide"
    )

    initialize_database()

    st.title("📚 Library Management System")
    st.sidebar.title("📚 Library Menu")

    menu = st.sidebar.radio(
        "Choose a Section",
        
[
    "Dashboard",
    "Add Book",
    "Delete Book",
    "All Books",
    "Search Books",
    "Register Member",
    "All Members",
    "Issue Book",
    "Issued Books",
    "Return Book",
    "Overdue Books"
]

    )

    st.sidebar.success("Database connected successfully!")

    if menu == "Dashboard":
        show_dashboard()

    elif menu == "Add Book":
        show_add_book()

    
    elif menu == "Delete Book":
        show_delete_book()


    elif menu == "All Books":
        show_all_books()

    elif menu == "Search Books":
        show_search_books()

    elif menu == "Register Member":
        show_register_member()

    elif menu == "All Members":
        show_all_members()

    elif menu == "Issue Book":
        show_issue_book()

    elif menu == "Issued Books":
        show_issued_books()

    elif menu == "Return Book":
        show_return_book()

    elif menu == "Overdue Books":
        show_overdue_books()


if __name__ == "__main__":
    main()
