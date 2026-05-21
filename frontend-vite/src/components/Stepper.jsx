function Stepper() {
  return (
    <section className="stepper-card">
      <div className="step active">
        <span>1</span>
        Configure
      </div>

      <div className="step-line"></div>

      <div className="step">
        <span>2</span>
        Upload File
      </div>

      <div className="step-line"></div>

      <div className="step">
        <span>3</span>
        Review & Run
      </div>
    </section>
  );
}

export default Stepper;