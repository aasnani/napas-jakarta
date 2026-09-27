import { Workspace } from "@/app/_components/workspace";
import styles from "./page.module.css";

export default function Page() {
  return (
    <>
      <Workspace />
      <footer className={styles.guideLinks}>
        <span>Learn how to read air-quality information for Jakarta:</span>
        <a href="/air-quality-jakarta" lang="en">
          PM2.5, PM10 and ISPU guide
        </a>
        <a href="/id/kualitas-udara-jakarta" lang="id">
          Panduan kualitas udara Jakarta
        </a>
      </footer>
    </>
  );
}
