from decimal import Decimal
from tronpy import Tron
from tronpy.keys import PrivateKey
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)

class TronPaymentHandler:
    def __init__(self):
        self.client = Tron(network='mainnet')
        self.private_key = PrivateKey(bytes.fromhex(settings.TRON_WALLET_PRIVATE_KEY))
        self.wallet_address = self.private_key.public_key.to_base58check_address()
        
    def get_trx_price(self):
        """Get current TRX price in USD"""
        try:
            response = requests.get('https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd')
            return Decimal(str(response.json()['tron']['usd']))
        except Exception as e:
            logger.error(f"Error getting TRX price: {e}")
            return Decimal('0.12')  # Fallback price
            
    def calculate_trx_amount(self, usd_amount):
        """Calculate TRX amount for given USD amount"""
        trx_price = self.get_trx_price()
        return Decimal(str(usd_amount)) / trx_price
        
    def create_payment(self, amount_usd, payment_id):
        """Create a new TRX payment"""
        try:
            trx_amount = self.calculate_trx_amount(amount_usd)
            
            # Create transaction
            txn = (
                self.client.trx.transfer(self.wallet_address, self.wallet_address, int(trx_amount * 1_000_000))
                .build()
                .sign(self.private_key)
            )
            
            # Get transaction ID
            tx_id = txn.txid
            
            return {
                'tx_id': tx_id,
                'trx_amount': trx_amount,
                'usd_amount': amount_usd,
                'payment_id': payment_id
            }
            
        except Exception as e:
            logger.error(f"Error creating TRX payment: {e}")
            raise
            
    def verify_payment(self, tx_id):
        """Verify if payment was successful"""
        try:
            tx = self.client.get_transaction(tx_id)
            return tx.get('ret')[0].get('contractRet') == 'SUCCESS'
        except Exception as e:
            logger.error(f"Error verifying TRX payment: {e}")
            return False
            
    def process_batch_payments(self, payments):
        """Process multiple payments in a single transaction"""
        try:
            total_amount = sum(p['amount'] for p in payments)
            trx_amount = self.calculate_trx_amount(total_amount)
            
            # Create batch transaction
            txn = (
                self.client.trx.transfer(self.wallet_address, self.wallet_address, int(trx_amount * 1_000_000))
                .build()
                .sign(self.private_key)
            )
            
            return {
                'tx_id': txn.txid,
                'trx_amount': trx_amount,
                'usd_amount': total_amount,
                'payment_count': len(payments)
            }
            
        except Exception as e:
            logger.error(f"Error processing batch payments: {e}")
            raise 