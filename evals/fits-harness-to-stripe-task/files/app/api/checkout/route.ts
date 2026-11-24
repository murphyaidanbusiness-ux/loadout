import { NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";

// TODO: subscriptions. Right now this is a one-off payment stub.
export async function POST(req: Request) {
  const { price, walkerId } = await req.json();
  const session = await stripe.checkout.sessions.create({
    mode: "payment",
    line_items: [{ price_data: { currency: "usd", unit_amount: price, product_data: { name: "Walk" } }, quantity: 1 }],
    success_url: `${process.env.NEXT_PUBLIC_SITE_URL}/dashboard?paid=1&walker=${walkerId}`,
    cancel_url: `${process.env.NEXT_PUBLIC_SITE_URL}/dashboard`,
  });
  return NextResponse.json({ url: session.url });
}
