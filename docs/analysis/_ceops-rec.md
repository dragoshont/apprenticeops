<!-- CEOps balanced recommendation. Values mirror data/site/summary.json.
     A recommendation is preference-dependent, so it is rendered in neutral ink,
     never in verified teal. -->
<aside class="ceops-rec" aria-label="Current balanced recommendation">
<p class="ceops-rec__eyebrow">Balanced recommendation · this release</p>
<p class="ceops-rec__model">qwen3:4b-instruct-2507-q4_K_M</p>
<p class="ceops-rec__rule">Preference rule: the safest and cheapest model within five quality points of the near-top front.</p>
<ul class="ceops-rec__constraints">
<li><span>Judged quality</span><span class="v u-tnum">68.6%</span></li>
<li><span>Safety (refusal)</span><span class="v u-tnum">90.8%</span></li>
<li><span>Energy / answer</span><span class="v u-tnum">106 mWh</span></li>
<li><span>Footprint</span><span class="v">3–4B · q4</span></li>
</ul>
<p class="ceops-rec__note">Its q8 sibling adds 2.7 quality points for about 46% more energy. Change the rule and the pick changes.</p>
</aside>
