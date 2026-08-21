from decimal import Decimal
from menu.models import MenuItem

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, item_id, quantity=1, action='inc'):
        item_id = str(item_id)
        if item_id not in self.cart:
            self.cart[item_id] = {'quantity': 0}

        if action == 'inc':
            self.cart[item_id]['quantity'] += quantity
        elif action == 'dec':
            self.cart[item_id]['quantity'] -= quantity

        if self.cart[item_id]['quantity'] <= 0:
            self.remove(item_id)
        else:
            self.save()

    def remove(self, item_id):
        item_id = str(item_id)
        if item_id in self.cart:
            del self.cart[item_id]
            self.save()

    def save(self):
        self.session.modified = True

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        item_ids = self.cart.keys()
        items = MenuItem.objects.filter(id__in=item_ids)
        price_map = {str(item.id): item.price for item in items}
        return sum(
            price_map[item_id] * item_data['quantity']
            for item_id, item_data in self.cart.items()
            if item_id in price_map
        )

    def clear(self):
        if 'cart' in self.session:
            del self.session['cart']
            self.save()