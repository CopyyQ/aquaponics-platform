import { Link } from "react-router-dom"
import { Button } from "@/shared/ui/button"
export function NotFoundCanonicalPage() { return <div className="grid min-h-[50vh] place-items-center text-center"><div><p className="text-6xl font-bold text-primary">404</p><h1 className="mt-4 text-2xl font-semibold">Không tìm thấy trang</h1><p className="mt-2 text-sm text-muted-foreground">Đường dẫn không tồn tại trong nền tảng vận hành.</p><Button className="mt-5" asChild><Link to="/aquaponics-systems">Về danh sách hệ thống</Link></Button></div></div> }
