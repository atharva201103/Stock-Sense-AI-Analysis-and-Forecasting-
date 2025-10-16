
import numpy as np
import matplotlib.pyplot as plt

# Mock data
dates = ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05']
prices = [140.67, 140.89, 141.05, 140.78, 141.23]

# Plotting
plt.figure(figsize=(10,6))
plt.plot(dates, prices, marker='o')
plt.title('Reliance Stock Price', fontsize=14, pad=20)
plt.xlabel('Date', fontsize=12)
plt.ylabel('Price (Rs)', fontsize=14)
plt.grid(True, alpha=0.3)
plt.savefig('media/b0fe5e1906cd474f8c56083c2544b358.png')
plt.close()
