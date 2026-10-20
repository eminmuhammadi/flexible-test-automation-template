from playwright.sync_api import APIRequestContext, APIResponse


class ProductsPage:
    BASE_URL = "https://fakestoreapi.com"

    def __init__(self, request: APIRequestContext) -> None:
        self._request = request

    def get_product(self, product_id: int) -> APIResponse:
        return self._request.get(f"{self.BASE_URL}/products/{product_id}")
