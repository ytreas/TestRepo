import logging
from odoo import models, fields, api
from datetime import datetime, timedelta
from collections import defaultdict

_logger = logging.getLogger(__name__)

class ProductRecommendation(models.Model):
    _inherit = "product.custom.price"

    def get_advanced_recommendations(self, user_id=None, session_id=None):
        """Get personalized product recommendations for a user or session."""
        
        # Step 1: Fetch user activity logs (last 50 activities)
        domain = []
        if user_id and session_id:
            domain = ['|', ("user_id", "=", user_id), ("session_id", "=", session_id)]
        elif user_id:
            domain = [("user_id", "=", user_id)]
        elif session_id:
            domain = [("session_id", "=", session_id)]

        activity_logs = self.env["user.activity.log"].sudo().search(domain, order='timestamp desc', limit=50)

        # Step 2: Define score weights
        score_weights = {"view": 3, "search": 3, "cart": 4, "purchase": 1}
        product_scores = defaultdict(float)  # Default score is 0

        # Step 3: Score products based on user activity
        for log in activity_logs:
            if log.product_id:
                product_scores[log.product_id.id] += score_weights.get(log.activity_type, 0)

    
        # Step 5: Sort products by score (descending)
        sorted_product_ids = sorted(
            product_scores.keys(), key=lambda x: product_scores[x], reverse=True
        )

        # Step 6: Get top 6 recommended products
        # recommended_products = self.browse(sorted_product_ids[:5]).exists()
        recommended_products = self.sudo().search([('id','in',sorted_product_ids[:5])])

        return recommended_products
    


    def get_trending_products(self):
        score_weights = {"view": 3, "search": 3, "cart": 4, "purchase": 1}
        product_scores = defaultdict(float)

        trending_logs = self.env["user.activity.log"].search([
            ("timestamp", ">=", datetime.now() - timedelta(days=7)),
            ("activity_type", "in", ["view", "search", "cart", "purchase"]),
        ])

        unique_products = set() 

        for log in trending_logs:
            if log.product_id:
                unique_products.add(log.product_id.id)  
                days_ago = (datetime.now() - log.timestamp).days
                decay_factor = max(0.5, (7 - days_ago) / 7)  
                product_scores[log.product_id.id] += score_weights.get(log.activity_type, 0) * decay_factor

        sorted_product_ids = sorted(unique_products, key=lambda x: product_scores[x], reverse=True)
        # _logger.info("Sorted product %s",sorted_product_ids)


        return self.browse(sorted_product_ids[:15]).exists()

