import { Link } from "react-router-dom"
import { Button } from "@/shared/ui/button"

export function NotFoundPage() { return <div className="grid min-h-[70vh] place-items-center text-center"><div><div className="text-7xl font-bold text-primary">404</div><h1 className="mt-4 text-2xl font-bold">Không tìm thấy trang</h1><p className="mt-2 text-muted-foreground">Đường dẫn không tồn tại trong hệ thống Aquaponics.</p><Button asChild className="mt-6"><Link to="/overview">Về Tổng quan</Link></Button></div></div> }
