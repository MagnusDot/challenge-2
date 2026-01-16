const transactionTypeTranslations = {
  'prelievo': 'Withdrawal',
  'bonifico': 'Bank Transfer',
  'domiciliazione': 'Recurring Payment',
  'pagamento e-comm': 'E-commerce Payment',
  'pagamento fisico': 'Physical Payment',
  'pagamento': 'Payment',
  'carta fisica': 'Physical Card',
  'carta': 'Card',
  '': 'Not specified'
};

export function translateTransactionType(type) {
  if (!type) return 'Not specified';
  return transactionTypeTranslations[type.toLowerCase()] || type;
}
