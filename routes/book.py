from flask import Blueprint, g, escape, session, redirect, render_template, request, jsonify, Response
from app import DAO
from Common.splunk_logger import log_to_splunk

from Controllers.UserManager import UserManager
from Controllers.BookManager import BookManager

book_view = Blueprint('book_routes', __name__, template_folder='/templates')

book_manager = BookManager(DAO)
user_manager = UserManager(DAO)

@book_view.route('/books/', defaults={'id': None})
@book_view.route('/books/<int:id>')
def home(id):
	user_manager.user.set_session(session, g)

	if id is not None:
		b = book_manager.getBook(id)
		log_to_splunk({
			'action': 'view_book_detail',
			'book_id': id,
			'user_id': user_manager.user.uid() if user_manager.user.isLoggedIn() else None,
			'ip': request.remote_addr
		})

		user_books = {}
		if user_manager.user.isLoggedIn():
			user_books = book_manager.getReserverdBooksByUser(user_id=user_manager.user.uid())['user_books'].split(',')
		
		if b and len(b) < 1:
			return render_template('book_view.html', error="No book found!")

		return render_template("book_view.html", books=b, g=g, user_books=user_books)
	else:
		b = book_manager.list()
		user_books = []

		if user_manager.user.isLoggedIn():
			reserved_books = book_manager.getReserverdBooksByUser(user_id=user_manager.user.uid())
			if reserved_books is not None:
				user_books = reserved_books['user_books'].split(',')

		log_to_splunk({
			'action': 'view_books_list',
			'user_id': user_manager.user.uid() if user_manager.user.isLoggedIn() else None,
			'book_count': len(b),
			'ip': request.remote_addr
		})

		if b and len(b) < 1:
			return render_template('books.html', error="No books found!")

		return render_template("books.html", books=b, g=g, user_books=user_books)

@book_view.route('/books/add/<id>', methods=['GET'])
@user_manager.user.login_required
def add(id):
	user_id = user_manager.user.uid()
	book_manager.reserve(user_id, id)

	log_to_splunk({
		'action': 'reserve_book',
		'user_id': user_id,
		'book_id': id,
		'ip': request.remote_addr
	})

	b = book_manager.list()
	user_manager.user.set_session(session, g)
	
	return render_template("books.html", msg="Book reserved", books=b, g=g)

@book_view.route('/books/search', methods=['GET'])
def search():
	user_manager.user.set_session(session, g)

	if "keyword" not in request.args:
		return render_template("search.html")

	keyword = request.args["keyword"]

	if len(keyword) < 1:
		return redirect('/books')

	d = book_manager.search(keyword)

	log_to_splunk({
		'action': 'search_books',
		'keyword': keyword,
		'result_count': len(d),
		'user_id': user_manager.user.uid() if user_manager.user.isLoggedIn() else None,
		'ip': request.remote_addr
	})

	if len(d) > 0:
		return render_template("books.html", search=True, books=d, count=len(d), keyword=escape(keyword), g=g)

	return render_template('books.html', error="No books found!", keyword=escape(keyword))
