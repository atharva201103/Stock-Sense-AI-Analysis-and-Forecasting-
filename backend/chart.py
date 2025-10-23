
import matplotlib.pyplot as plt

plt.figure(figsize=(10, 6))
plt.plot('SBIN', data['Price'], label='SBIN')
plt.plot('TCS', data['Price'], label='TCS')
plt.title('India Stock Market Performance')
plt.xlabel('Time')
plt.ylabel('Price (₹)')
plt.legend()
plt.grid(True)
plt.savefig('media/d17a5578aca9407aae5ca344dd7cc341.png')
plt.close()
