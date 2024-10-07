from flask import Blueprint, render_template, flash, redirect, request, jsonify, url_for
from flask_login import login_required, current_user
from .models import Product, Cart, Order
from . import db
import paypalrestsdk

views = Blueprint('views', __name__)

# PayPal SDK Configuration
paypalrestsdk.configure({
    "mode": "sandbox",  # Change to "live" for production
    "client_id": 'YOUR_CLIENT_ID',  # Replace with your PayPal client ID
    "client_secret": 'YOUR_CLIENT_SECRET'  # Replace with your PayPal client secret
})

@views.route('/')
def home():
    items = Product.query.filter_by(flash_sale=True).all()
    cart = Cart.query.filter_by(customer_link=current_user.id).all() if current_user.is_authenticated else []
    return render_template('home.html', items=items, cart=cart)

@views.route('/add-to-cart/<int:item_id>', methods=['POST'])
@login_required
def add_to_cart(item_id):
    item_to_add = Product.query.get(item_id)
    if not item_to_add:
        flash('Item not found.', 'error')
        return redirect(request.referrer)

    item_exists = Cart.query.filter_by(product_link=item_id, customer_link=current_user.id).first()
    if item_exists:
        try:
            item_exists.quantity += 1
            db.session.commit()
            flash(f'Quantity of {item_exists.product.product_name} has been updated', 'success')
        except Exception as e:
            print('Quantity not updated:', e)
            flash(f'Quantity of {item_exists.product.product_name} not updated', 'error')
    else:
        new_cart_item = Cart(quantity=1, product_link=item_to_add.id, customer_link=current_user.id)
        try:
            db.session.add(new_cart_item)
            db.session.commit()
            flash(f'{new_cart_item.product.product_name} added to cart', 'success')
        except Exception as e:
            print('Item not added to cart:', e)
            flash(f'{new_cart_item.product.product_name} has not been added to cart', 'error')

    return redirect(request.referrer)

@views.route('/cart')
@login_required
def show_cart():
    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)
    return render_template('cart.html', cart=cart, amount=amount, total=amount )

@views.route('/pluscart')
@login_required
def plus_cart():
    cart_id = request.args.get('cart_id')
    cart_item = Cart.query.get(cart_id)
    if cart_item:
        cart_item.quantity += 1
        db.session.commit()

    return update_cart_response()

@views.route('/minuscart')
@login_required
def minus_cart():
    cart_id = request.args.get('cart_id')
    cart_item = Cart.query.get(cart_id)
    if cart_item and cart_item.quantity > 1:
        cart_item.quantity -= 1
        db.session.commit()

    return update_cart_response()

@views.route('/removecart')
@login_required
def remove_cart():
    cart_id = request.args.get('cart_id')
    cart_item = Cart.query.get(cart_id)
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()

    return update_cart_response()

def update_cart_response():
    cart = Cart.query.filter_by(customer_link=current_user.id).all()
    amount = sum(item.product.current_price * item.quantity for item in cart)

    data = {
        'quantity': len(cart),  # Change to total items in cart
        'amount': amount,
        'total': amount   # Include shipping fee
    }
    return jsonify(data)

@views.route('/place-order', methods=['POST'])
@login_required
def place_order():
    customer_cart = Cart.query.filter_by(customer_link=current_user.id).all()
    if customer_cart:
        try:
            # Calculate total without shipping
            total = sum(item.product.current_price * item.quantity for item in customer_cart)  # Removed shipping
            total_amount = str(total)  # Convert to string for PayPal

            items = [{
                "name": item.product.product_name,
                "sku": item.product.id,
                "price": str(item.product.current_price),  # Convert to string
                "currency": "USD",
                "quantity": item.quantity
            } for item in customer_cart]

            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": url_for('views.payment_success', _external=True),
                    "cancel_url": url_for('views.payment_cancel', _external=True)
                },
                "transactions": [{
                    "item_list": {
                        "items": items
                    },
                    "amount": {
                        "total": total_amount,  # Ensure this matches the total of items only
                        "currency": "USD"
                    },
                    "description": "Purchase of goods"
                }]
            })

            if payment.create():
                for link in payment.links:
                    if link.rel == "approval_url":
                        return redirect(link.href)  # Redirect the user to PayPal for approval
            else:
                flash(f'Payment could not be created: {payment.error}', 'error')
                return redirect('/')

        except Exception as e:
            print(e)
            flash('An error occurred while placing the order', 'error')
            return redirect('/')

    else:
        flash('Your cart is empty', 'error')
        return redirect('/')

@views.route('/payment-success')
def payment_success():
    payment_id = request.args.get('paymentId')
    payer_id = request.args.get('PayerID')

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        for item in Cart.query.filter_by(customer_link=current_user.id).all():
            total_price = item.product.current_price * item.quantity
            
            # Create the order object with the updated attributes
            order = Order(
                product_link=item.product_link,
                customer_link=current_user.id,
                quantity=item.quantity,
                price=total_price,  # Set the price to the total price of this item
                status='Completed',  # Set the order status
                payment_id=payment_id  # Store the payment ID for tracking
            )
            db.session.add(order)  # Store order in database
            db.session.delete(item)  # Remove item from cart
        db.session.commit()
        flash('Payment completed successfully!', 'success')
        return redirect('/orders')
    else:
        flash('Payment execution failed', 'error')
        return redirect('/')
    

@views.route('/payment-cancel')
def payment_cancel():
    flash('Payment was cancelled', 'warning')
    return redirect('/cart')

@views.route('/orders')
@login_required
def order():
    orders = Order.query.filter_by(customer_link=current_user.id).all()
    return render_template('orders.html', orders=orders)

@views.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        search_query = request.form.get('search')
        items = Product.query.filter(Product.product_name.ilike(f'%{search_query}%')).all()
        return render_template('search.html', items=items, cart=Cart.query.filter_by(customer_link=current_user.id).all() if current_user.is_authenticated else [])

    return render_template('search.html')

@views.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']
        flash(f"Thank you for your message, {name}! We'll get back to you shortly.", 'success')
        return redirect(url_for('views.contact'))
    
    return render_template('contact.html')

@views.route('/about')
def about():
    return render_template('about.html')

@views.route('/products')
def product_list():
    items = Product.query.all()
    return render_template('product_list.html', items=items)

# Main Flask app creation
from website import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)  # Run the app in debug mode
