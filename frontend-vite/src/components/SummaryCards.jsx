function SummaryCards({ summary }) {
  const cards = [
    {
      label: "Total Rows",
      value: summary.total_rows,
      tone: "blue",
      icon: "▣",
    },
    {
      label: "Valid IDs",
      value: summary.valid_ids,
      tone: "green",
      icon: "🛡",
      badge: "60%",
    },
    {
      label: "Invalid IDs",
      value: summary.invalid_ids,
      tone: "red",
      icon: "⚠",
      badge: "40%",
    },
    {
      label: "Clean Records",
      value: summary.clean_records,
      tone: "purple",
      icon: "◎",
    },
    {
      label: "Processing Time",
      value: summary.processing_time,
      tone: "orange",
      icon: "◷",
    },
  ];

  return (
    <div className="summary-grid">
      {cards.map((card) => (
        <div className={`summary-card ${card.tone}`} key={card.label}>
          <div>
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            {card.badge && <em>{card.badge}</em>}
          </div>

          <div className="summary-icon">{card.icon}</div>
        </div>
      ))}
    </div>
  );
}

export default SummaryCards;