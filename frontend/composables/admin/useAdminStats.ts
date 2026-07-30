import type { Reservation, Transaction, User } from "~/types/api";

export const useAdminStats = () => {
  const api = useApi();
  const users = ref<User[]>([]);
  const transactions = ref<Transaction[]>([]);
  const reservations = ref<Reservation[]>([]);
  const loading = ref(false);

  const load = async () => {
    loading.value = true;
    try {
      const [userRows, transactionRows, reservationRows] = await Promise.all([
        api.users.getAll(),
        api.transactions.getAll(),
        api.reservations.getAll()
      ]);
      users.value = userRows;
      transactions.value = transactionRows;
      reservations.value = reservationRows;
    } finally {
      loading.value = false;
    }
  };

  const summary = computed(() => {
    const totalCharges = transactions.value
      .filter((transaction) => transaction.type === "charge")
      .reduce((total, transaction) => total + Number(transaction.amount), 0);
    const totalSales = transactions.value
      .filter((transaction) => transaction.type === "deduct")
      .reduce((total, transaction) => total + Math.abs(Number(transaction.amount)), 0);
    const totalRefunds = transactions.value
      .filter((transaction) => transaction.type === "refund")
      .reduce((total, transaction) => total + Math.abs(Number(transaction.amount)), 0);

    return {
      totalUsersCount: users.value.length,
      totalAdminsCount: users.value.filter((user) => user.role === "admin").length,
      activeTicketsCount: reservations.value.filter((reservation) => reservation.status === "reserved").length,
      totalCharges,
      totalSales,
      totalRefunds
    };
  });

  return { users, transactions, reservations, loading, summary, load };
};
