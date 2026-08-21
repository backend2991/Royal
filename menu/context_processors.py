def table_context(request):
    """Makes the current table number (from ?table=N, remembered in session)
    available to every template — used by the persistent 'Table N' badge and
    by the order form's hidden input."""
    table_number = request.GET.get("table") or request.session.get("table_number")
    return {"current_table_number": table_number}


from orders.carts import Cart

def cart(request):
    return {
        'cart': Cart(request)
    }
