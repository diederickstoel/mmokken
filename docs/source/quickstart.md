# Quickstart

```python
import numpy as np
from mmokken import aisp, coefH

X = np.array(...)  # respondents × items, integer 0..k

assignment = aisp(X, lowerbound=0.3)
h_stats = coefH(X, se=False)
print(h_stats["H"], h_stats["Hi"])
```

See [API reference](api/index) for the full surface; see
[research programme](https://github.com/dstoel/mmokken/blob/main/docs/research_proposal.docx)
for the conceptual frame.
