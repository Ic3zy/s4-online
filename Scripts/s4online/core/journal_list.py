class OpObject:
    def __init__(self, op, client_id):
        self.op = op
        self.client_id = client_id


class S4OnlineProxyList:
    """
    Oyun motoru ile saf Python listesi arasında duran,
    gelen tüm metod çağrılarını bodoslama orijinal listeye
    yönlendiren katıksız proxy (köprü) sınıfı.
    """

    def __init__(self, iterable=None):
        self._data = [] if iterable is None else list(iterable)
        self._custom_ops = []

    def __len__(self):
        return self._data.__len__()

    def __getitem__(self, index):
        return self._data.__getitem__(index)

    def __setitem__(self, index, value):
        return self._data.__setitem__(index, value)

    def __delitem__(self, index):
        return self._data.__delitem__(index)

    def __iter__(self):
        return self._data.__iter__()

    def __contains__(self, item):
        return self._data.__contains__(item)

    def __repr__(self):
        return self._data.__repr__()

    def get_custom_ops(self):
        return self._custom_ops

    def get_custom_op(self, index):
        return self._custom_ops[index]

    def append(self, item):
        if isinstance(item, OpObject):
            self._custom_ops.append(item)
            return self._data.append(item.op)
        return self._data.append(item)

    def extend(self, iterable):
        for op in iterable:
            self.append(op)  # Kodu amelelikten kurtarıp append'e paslıyoruz

    def insert(self, index, item):
        if isinstance(item, OpObject):
            self._custom_ops.insert(index, item)
            self._data.insert(index, item.op)
        else:
            self._data.insert(index, item)

    def pop(self, index=-1):
        """Oyun motoru pop ettiğinde iki havuzdan da senkronize düşüyoruz."""
        popped_item = self._data.pop(index)

        # _custom_ops içindeki izdüşümünü de güvenle temizle
        # Tersten indeks döngüsü ile sinsi bug barajını aşıyoruz
        target = next((op for op in self._custom_ops if op.op == popped_item), None)

        if target:
            self._custom_ops.remove(target)

        return popped_item

    def remove(self, item):
        """Bulduğu ilk yerde iki taraftan da siler ve kurallara göre güvenle kaçar."""
        for i in range(len(self._custom_ops)):
            if self._custom_ops[i].op == item:
                self._custom_ops.pop(i)
                break

        return self._data.remove(item)

    def clear(self):
        self._data = []
        self._custom_ops = []

    def copy(self):
        # NOT: Bir önceki adımda konuştuğumuz gibi listeyi değil,
        # nesnenin kendisini kopyalamak istiyorsan burayı self.__class__(self._data) yapabilirsin.
        # Ama oyun motorunun beklediği gibi klon veri istiyorsan bu hali de temizdir.
        return self.__class__(self._data.copy())

    def count(self, item):
        return self._data.count(item)

    def index(self, item, *args):
        return self._data.index(item, *args)

    def reverse(self):
        return self._data.reverse()

    def sort(self, *args, **kwargs):
        return self._data.sort(*args, **kwargs)
