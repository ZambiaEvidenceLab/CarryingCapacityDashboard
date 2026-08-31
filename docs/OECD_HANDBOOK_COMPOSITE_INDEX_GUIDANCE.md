# OECD Handbook on Constructing Composite Indicators — Applied Reference

> Source: OECD/JRC (2008), *Handbook on Constructing Composite Indicators: Methodology and User Guide*. Selected guidance relevant to constructing a sub-national health composite index with input, access, and outcome dimensions.

---

## The 10-Step Pipeline

The handbook defines a sequential but iterative pipeline. "Choices made in one step can have important implications for others: therefore, the composite indicator builder has not only to make the most appropriate methodological choices in each step, but also to identify whether they fit together well."

| Step | What | Key Decision |
|------|------|-------------|
| 1 | Theoretical framework | Define what you're measuring; distinguish inputs/outputs/processes |
| 2 | Data selection | Indicator quality, coverage, proxy variables |
| 3 | Missing data imputation | Single vs. multiple imputation |
| 4 | Multivariate analysis | PCA, factor analysis, cluster analysis to understand data structure |
| 5 | Normalisation | Make indicators comparable (z-scores, min-max, ranks, etc.) |
| 6 | Weighting & aggregation | Equal/statistical/participatory weights; linear/geometric/multi-criteria aggregation |
| 7 | Uncertainty & sensitivity analysis | Monte Carlo robustness testing |
| 8 | Back to the details | Decompose index; identify drivers via path analysis |
| 9 | Links to other variables | Correlate index with external validators |
| 10 | Presentation & visualisation | Communicate results to policy audience |

---

## Step 1: Theoretical Framework

"What is badly defined is likely to be badly measured."

"A sound theoretical framework is the starting point in constructing composite indicators. The framework should clearly define the phenomenon to be measured and its sub-components, selecting individual indicators and weights that reflect their relative importance and the dimensions of the overall composite. This process should ideally be based on what is desirable to measure and not on which indicators are available."

Requirements:

1. **Define the concept.** "The definition should give the reader a clear sense of what is being measured by the composite indicator. It should refer to the theoretical framework, linking various sub-groups and the underlying indicators."

2. **Determine sub-groups.** "Multi-dimensional concepts can be divided into several sub-groups. These sub-groups need not be (statistically) independent of each other, and existing linkages should be described theoretically or empirically to the greatest extent possible." "Such a nested structure improves the user's understanding of the driving forces behind the composite indicator. It may also make it easier to determine the relative weights across different factors."

3. **Identify indicator types.** "The selection criteria should work as a guide to whether an indicator should be included or not in the overall composite index. It should be as precise as possible and should describe the phenomenon being measured, i.e. input, output or process." **Warning:** "Too often composite indicators include both input and output measures. For example, an Innovation Index could combine R&D expenditures (inputs) and the number of new products and services (outputs) in order to measure the scope of innovative activity in a given country. However, only the latter set of output indicators should be included (or expressed in terms of output per unit of input) if the index is intended to measure innovation performance."

4. **Involve experts and stakeholders.** "This step... should involve experts and stakeholders as much as possible, in order to take into account multiple viewpoints and to increase the robustness of the conceptual framework and set of indicators."

**Deliverable:**
- Clear understanding and definition of the multi-dimensional phenomenon to be measured
- Nested structure of the various sub-groups of the phenomenon
- List of selection criteria for the underlying variables, e.g. input, output, process
- Clear documentation of the above

---

## Step 2: Data Selection

"A composite indicator is above all the sum of its parts."

"Indicators should be selected on the basis of their relevance, analytical soundness, timeliness, accessibility, etc."

"While the choice of indicators must be guided by the theoretical framework for the composite, the data selection process can be quite subjective as there may be no single definitive set of indicators."

**On proxy variables:** "Proxy measures can be used when the desired data are unavailable or when cross-country comparability is limited... caution must be taken in the utilisation of proxy indicators. To the extent that data permit, the accuracy of proxy measures should be checked through correlation and sensitivity analysis."

**On size-dependence:** "The builder should also pay close attention to whether the indicator in question is dependent on GDP or other size-related factors. To have an objective comparison across small and large countries, scaling of variables by an appropriate size measure, e.g. population, income, trade volume, and populated land area, etc. is required."

**On data quality:** "The quality and accuracy of composite indicators should evolve in parallel with improvements in data collection and indicator development." "We do not marry the idea that using what is available is necessarily enough. Poor data will produce poor results in a garbage-in, garbage-out logic."

**Deliverable:**
- Checked the quality of the available indicators
- Discussed the strengths and weaknesses of each selected indicator
- Created a summary table on data characteristics, e.g. availability (across country, time), source, type (hard, soft or input, output, process)

---

## Step 3: Missing Data Imputation

"The idea of imputation could be both seductive and dangerous."

Missing data patterns:
- **MCAR** (Missing Completely At Random): "Missing values do not depend on the variable of interest or on any other observed variable in the data set."
- **MAR** (Missing At Random): "Missing values do not depend on the variable of interest, but are conditional on other variables in the data set."
- **NMAR** (Not Missing At Random): "Missing values depend on the values themselves."

"Unfortunately, there is no statistical test for NMAR and often no basis on which to judge whether data are missing at random or systematically."

**Rule of thumb:** "If a variable has more than 5% missing values, cases are not deleted." (Little & Rubin, 2002)

**Methods:**
1. **Case deletion** — "ignores possible systematic differences between complete and incomplete samples and produces unbiased estimates only if deleted records are a random sub-sample of the original sample (MCAR assumption)."
2. **Single imputation** (mean/median substitution, regression imputation, EM imputation) — "known to underestimate the variance, because it partially reflects the imputation uncertainty."
3. **Multiple imputation** — "provides several values for each missing value, can more effectively represent the uncertainty due to imputation."

"No imputation model is free of assumptions and the imputation results should hence be thoroughly checked for their statistical properties, such as distributional characteristics, as well as heuristically for their meaningfulness."

**Deliverable:**
- Complete data set without missing values
- Measure of the reliability of each imputed value so as to explore the impact of imputation on the composite indicator
- Discussed the presence of outliers in the dataset
- Documented and explained the selected imputation procedures and the results

---

## Step 4: Multivariate Analysis

"Analysing the underlying structure of the data is still an art."

"The underlying nature of the data needs to be carefully analysed before the construction of a composite indicator. This preliminary step is helpful in assessing the suitability of the data set and will provide an understanding of the implications of the methodological choices, e.g. weighting and aggregation, during the construction phase."

### A. Indicator structure (PCA / Factor Analysis / Cronbach's Alpha)

"The analyst must first decide whether the nested structure of the composite indicator is well defined (see Step 1) and whether the set of available individual indicators is sufficient or appropriate to describe the phenomenon."

"The goal of principal components analysis (PCA) is to reveal how different variables change in relation to each other and how they are associated." "Factor analysis (FA) is similar to PCA, but is based on a particular statistical model."

"An alternative way to investigate the degree of correlation among a set of variables is to use the Cronbach coefficient alpha (c-alpha), which is the most common estimate of internal consistency of items in a model or survey."

**Caution:** "It is important to avoid carrying out multivariate analysis if the sample is small compared to the number of indicators, since results will not have known statistical properties."

**Strengths and weaknesses of PCA/FA:**
- Strengths: "Can summarise a set of individual indicators while preserving the maximum possible proportion of the total variation." "Largest factor loadings are assigned to the individual indicators that have the largest variation across countries, a desirable property for cross-country comparisons."
- Weaknesses: "Correlations do not necessarily represent the real influence of the individual indicators on the phenomenon being measured." "Sensitive to modifications in the basic data." "Sensitive to the presence of outliers." "Sensitive to small-sample problems."

### B. Unit grouping (Cluster Analysis)

"Cluster analysis is another tool for classifying large amounts of information into manageable sets." It serves as: "(i) a purely statistical method of aggregation, (ii) a diagnostic tool for exploring the impact of methodological choices, (iii) a method of disseminating information without losing that on the dimensions of the individual indicators, and (iv) a method for selecting groups for the imputation of missing data with a view to decreasing the variance of the imputed values."

**Deliverable:**
- Checked the underlying structure of the data along various dimensions (indicators, units)
- Applied the suitable multivariate methodology (PCA, FA, cluster analysis)
- Identified sub-groups of indicators or groups of units that are statistically "similar"
- Analysed the structure of the data set and compared this to the theoretical framework
- Documented the results and the interpretation of the components and factors

---

## Step 5: Normalisation

"Avoid adding up apples and oranges."

"Normalisation is required prior to any data aggregation as the indicators in a data set often have different measurement units."

| Method | Characteristics |
|--------|----------------|
| **Ranking** | "Simplest normalisation technique. Not affected by outliers. Country performance in absolute terms however cannot be evaluated as information on levels is lost." |
| **Z-scores** | "Converts indicators to a common scale with a mean of zero and standard deviation of one. Indicators with extreme values thus have a greater effect on the composite indicator." |
| **Min-Max** | "Normalises indicators to have an identical range [0, 1] by subtracting the minimum value and dividing by the range. However, extreme values/outliers could distort the transformed indicator." |
| **Distance to reference** | "Measures the relative position of a given indicator vis-à-vis a reference point. This could be a target to be reached in a given time frame." |
| **Categorical scales** | "Assigns a score for each indicator. Categorical scales exclude large amounts of information about the variance of the transformed indicators." |

"The selection of a suitable method, however, is not trivial and deserves special attention to eventual scale adjustments or transformation of highly skewed indicators. The normalisation method should take into account the data properties, as well as the objectives of the composite indicator. Robustness tests might be needed to assess their impact on the outcomes."

**Deliverable:**
- Selected the appropriate normalisation procedure(s) with reference to the theoretical framework and to the properties of the data
- Made scale adjustments, if necessary
- Transformed highly skewed indicators, if necessary
- Documented and explained the selected normalisation procedure and the results

---

## Step 6: Weighting and Aggregation

### Weighting

"The relative importance of the indicators is a source of contention."

"Most composite indicators rely on equal weighting (EW), i.e. all variables are given the same weight. This essentially implies that all variables are 'worth' the same in the composite, but it could also disguise the absence of a statistical or an empirical basis, e.g. when there is insufficient knowledge of causal relationships or a lack of consensus on the alternative. In any case, equal weighting does not mean 'no weights', but implicitly implies that the weights are equal."

**Unbalanced structure warning:** "If variables are grouped into dimensions and those are further aggregated into the composite, then applying equal weighting to the variables may imply an unequal weighting of the dimension (the dimensions grouping the larger number of variables will have higher weight). This could result in an unbalanced structure in the composite index."

**On double-counting:** "When using equal weights, it may happen that — by combining variables with a high degree of correlation — an element of double counting may be introduced into the index: if two collinear indicators are included in the composite index with a weight of w₁ and w₂, the unique dimension that the two indicators measure would have weight (w₁ + w₂) in the composite." "A rule of thumb should be introduced to define a threshold beyond which the correlation is a symptom of double counting. On the other hand, relating correlation analysis to weighting could be dangerous when motivated by apparent redundancy." "Double counting should not only be determined by statistical analysis but also by the analysis of the indicator itself vis-à-vis the rest of indicators and the phenomenon they all aim to capture."

**Available weighting methods:**

| Method | Characteristics |
|--------|----------------|
| **Equal weighting (EW)** | Most common. Transparent. "Could also disguise the absence of a statistical or an empirical basis." |
| **PCA/FA weights** | Data-driven. "Weights, however, cannot be estimated with these methods if no correlation exists between indicators." |
| **Budget Allocation (BAP)** | Experts distribute points. "Optimal for a maximum of 10-12 indicators. If too many indicators are involved, this method can induce serious cognitive stress." |
| **Analytic Hierarchy Process (AHP)** | Pairwise comparisons. "Computationally costly, but results in a set of weights that is less sensitive to errors of judgement." Inconsistency ratio should be < 0.1. |
| **Benefit of the Doubt (BOD/DEA)** | "Extremely parsimonious about weighting assumptions as they allow the data to decide on the weights and are sensitive to national priorities. However, with BOD weights are country specific and have a number of estimation problems." |
| **Conjoint Analysis (CA)** | "Asks for an evaluation of a set of alternative scenarios." "Implies compensability among indicators." |

"The absence of an 'objective' way to determine weights and aggregation methods does not necessarily lead to rejection of the validity of composite indicators, as long as the entire process is transparent."

### Aggregation

**Linear (additive):** "By far the most widespread." "Although widely used, this aggregation imposes restrictions on the nature of individual indicators." "An additive aggregation function exists if and only if these indicators are mutually preferentially independent" — meaning "the trade-off ratio between two variables is independent of the values of the Q-2 other variables."

"Furthermore, linear aggregations reward base-indicators proportionally to the weights, while geometric aggregations reward those countries with higher scores."

"In both linear and geometric aggregations, weights express trade-offs between indicators. A deficit in one dimension can thus be offset (compensated) by a surplus in another."

**Geometric:** "An undesirable feature of additive aggregations is the implied full compensability, such that poor performance in some indicators can be compensated for by sufficiently high values in other indicators." Geometric aggregation is "an in-between solution."

"In a benchmarking exercise, countries with low scores in some individual indicators thus would prefer a linear rather than a geometric aggregation. On the other hand, the marginal utility of an increase in the score would be much higher when the absolute value of the score is low... Consequently, a country would have a greater incentive to address those sectors/activities/alternatives with low scores if the aggregation were geometric rather than linear, as this would give it a better chance of improving its position in the ranking."

**Non-compensatory MCA:** "To ensure that weights remain a measure of importance, other aggregation methods should be used, in particular methods that do not allow compensability. Moreover, if different goals are equally legitimate and important, a non-compensatory logic might be necessary. This is usually the case when highly different dimensions are aggregated in the composite, as in the case of environmental indices that include physical, social and economic data."

**Deliverable:**
- Selected the appropriate weighting and aggregation procedure(s) with reference to the theoretical framework
- Considered the possibility of using alternative methods (multi-modelling principle)
- Discussed whether correlation issues among indicators should be accounted for
- Discussed whether compensability among indicators should be allowed
- Documented and explained the weighting and aggregation procedures selected

---

## Step 7: Uncertainty and Sensitivity Analysis

"Sensitivity analysis is considered a necessary requirement in econometric practice and has been defined as the modeller's equivalent of orthopaedists' X-rays."

"Since the quality of a model also depends on the soundness of its assumptions, good modelling practice requires that the modeller provide an evaluation of the confidence in the model, assessing the uncertainties associated with the modelling process and the subjective choices taken."

"A combination of uncertainty and sensitivity analysis can help to gauge the robustness of the composite indicator ranking, to increase its transparency, to identify which countries are favoured or weakened under certain assumptions and to help frame a debate around the index."

### Sources of uncertainty to test

The handbook recommends varying all of these simultaneously in a single Monte Carlo experiment:

1. Inclusion and exclusion of individual indicators
2. Modelling data error based on available variance estimation
3. Using alternative editing schemes (e.g. single or multiple imputation)
4. Using alternative normalisation schemes (min-max, z-scores, ranks)
5. Using different weighting schemes (participatory, endogenous, equal)
6. Using different aggregation systems (linear, geometric, multi-criteria)
7. Using different plausible values for the weights

### Uncertainty analysis

"The results of the robustness analysis are generally reported as country rankings with their related uncertainty bounds, which are due to the uncertainties at play. This makes it possible to communicate to the user the plausible range of the composite indicator values for each country."

### Sensitivity analysis (Sobol' variance-based method)

"The sensitivity analysis results are generally shown in terms of the sensitivity measure for each input source of uncertainty. These sensitivity measures represent how much the uncertainty in the composite indicator for a country would be reduced if that particular input source of uncertainty were removed."

Two key measures:
- **First-order index (Sᵢ):** The fraction of output variance attributable to uncertainty in factor Xᵢ alone.
- **Total-effect index (STᵢ):** The fraction of output variance attributable to factor Xᵢ including all its interactions with other factors. "A significant difference between STᵢ and Sᵢ signals an important interaction role for that factor."

**Average rank shift statistic:** "The average of the absolute differences in countries' ranks with respect to a reference ranking over the M countries."

### Key empirical findings from the handbook's TAI analysis

- "The aggregation system, followed by the inclusion/exclusion of individual indicators and expert selection, is the most influential input factors."
- "The countries with the highest total variance in ranks are the middle-of-the-table countries, while the leaders and laggards... have low total variance."
- "If the constructors of the index disagree on the aggregation system, it is highly unlikely that a robust index will emerge."
- "If uncertainties exist in the context of a well-established theoretical framework, e.g. if a participatory approach within a linear aggregation scheme is favoured, the resulting country rankings could be fairly robust in spite of the uncertainties."
- "Neither imputation nor normalisation significantly affect countries' rankings when uncertainties of higher order are present."
- "When the weights are uncertain, it is unlikely that normalisation and editing will affect the country ranks."

**Deliverable:**
- Identified the sources of uncertainty in the development of the composite indicator
- Assessed the impact of the uncertainties/assumptions on the final result
- Conducted sensitivity analysis of the inference, e.g. to show what sources of uncertainty are more influential in determining the relative ranking of two entities
- Documented and explained the sensitivity analyses and the results

---

## Step 8: Back to the Details

"De-constructing composite indicators can help extend the analysis."

"Composite indicators provide a starting point for analysis. While they can be used as summary indicators to guide policy and data work, they can also be decomposed such that the contribution of sub-components and individual indicators can be identified and the analysis of country performance extended."

### Decomposition visualisations

The handbook demonstrates four approaches:
1. **Stacked bar charts** — contribution of each sub-component to the total score
2. **Leader/laggard plots** — each indicator's range across all units, with a specific unit highlighted
3. **Spider/radar diagrams** — a unit compared to the top performers and another reference unit
4. **Traffic light tables** — colour-coded performance by indicator (well below average / below average / average / above average / well above average)

### Path analysis

"Path analysis, conceived by the biologist S. Wright in the 1920s, is an extension of regression analysis in which many endogenous and exogenous variables can be analysed simultaneously."

"The standardised regression coefficients emerging from this estimation will be used as path coefficients. The total effect of A on D will be the sum of the direct effect represented by the path coefficient relating A to D and of the indirect effect through its correlation with B."

"A high value... corroborates the relationship..., whereas a low value would point to the absence of a linear relationship."

**Critical caveat:** "Path analysis cannot be used to infer causality, given its confirmatory nature: the causal relationship has to be modelled in advance." "Correlation does not mean causality."

### Structural Equation Modelling (SEM)

"SEM is an extension of the general linear model that simultaneously estimates relationships between multiple independent, dependent and latent variables... the advantages of SEM are its generality (it includes path analysis and multivariate regression as special cases) and the possibility of including latent variables or factors as nodes. This is particularly useful when working with composite indicators, given that in most cases the available indicators only imperfectly measure theoretical concepts."

**Deliverable:**
- Decomposed the composite indicator into its individual parts and tested for correlation and causality (if possible)
- Profiled unit performance at the indicator level to reveal what is driving the composite indicator results, and in particular whether the composite indicator is overly dominated by a small number of indicators
- Documented and explained the relative importance of the sub-components

---

## Step 9: Links to Other Variables

"Composite indicators often measure concepts that are linked to well-known and measurable phenomena. These links can be used to test the explanatory power of a composite."

"An indicator measuring the environment for business start-ups, for example, could be linked to entry rates of new firms, where good performance on the composite indicator of business environment would be expected to yield higher entry rates."

**On circularity:** "It should be noted that composite indicators often include some of the indicators with which they are being correlated, leading to double counting. For example, most composite indicators of sustainable development include some measure of GDP as a sub-component. In such cases, the GDP measure should be removed from the composite indicator before running any correlation."

**Monte Carlo validation of correlations:** "The impact of the weights (or normalisation method, or other) on the degree of correlation between a composite indicator and another variable of interest can be evaluated in a Monte Carlo framework. At each simulation, a weight can, for example, be allowed to vary between 0 and 1 and the simulated weights for all the indicators are then divided by the overall sum of the weights. This simulation is repeated 10,000 times and the composite indicator scores for each country are calculated 10,000 times. The correlation coefficient can thus be calculated for each simulation and the highest, median and lowest possible correlation determined."

**On causality:** "Correlation analysis should not be mistaken with causality analysis. Correlation simply indicates that the variation in the two data sets is similar... The causality remains unclear in the correlation analysis."

**Deliverable:**
- Correlated the composite indicator with related measurable phenomena
- Tested the links with variations of the composite indicator as determined through sensitivity analysis
- Developed data-driven narratives on the results
- Documented and explained the correlations and the results

---

## Step 10: Presentation and Visualisation

"A well-designed graph can speak louder than words."

"Composite indicators must be able to communicate a story to decision-makers and other end-users quickly and accurately. Tables, albeit providing the complete information, can sometimes obscure sensitive issues immediately visible with a graphical representation."

The handbook demonstrates:
- **Tabular format** — "simplest presentation, in which the composite indicator is presented for each country as a table of values. Usually countries are displayed in descending rank order."
- **Bar charts** — "The top bar indicates the average performance of all countries and enables the reader to identify how a country is performing vis-à-vis the average."
- **Line charts** — "Can be used to illustrate the changes of a composite (or its dimensions/components) across time."
- **Trend diagrams** — plotting level on one axis and trend on another, creating quadrants: "moving ahead", "catching up", "losing momentum", "falling further behind."

**Deliverable:**
- Identified a coherent set of presentational tools for the target audience
- Selected the visualisation technique which communicates the most information
- Visualised the results of the composite indicator in a clear and accurate manner

---

## Quality Framework Summary

The handbook maps each construction step to the quality dimensions it affects:

| Step | Relevance | Accuracy | Credibility | Timeliness | Accessibility | Interpretability | Coherence |
|------|-----------|----------|-------------|------------|---------------|-----------------|-----------|
| Theoretical framework | ✓ | | ✓ | | | ✓ | |
| Data selection | | ✓ | ✓ | ✓ | | | |
| Imputation | | ✓ | ✓ | | | | |
| Multivariate analysis | | ✓ | | | | ✓ | |
| Normalisation | | ✓ | | | | ✓ | ✓ |
| Weighting & aggregation | | ✓ | ✓ | | | ✓ | ✓ |
| Robustness & sensitivity | | ✓ | ✓ | | | ✓ | |
| Back to the data | ✓ | | ✓ | | | ✓ | |
| Links to other variables | ✓ | | ✓ | | | ✓ | |
| Visualisation | ✓ | | | | ✓ | ✓ | |
| Dissemination | ✓ | | ✓ | | ✓ | ✓ | |

"The overall quality of the composite indicator depends on several aspects, related both to the quality of elementary data used to build the indicator and the soundness of the procedures used in its construction."

"A composite based on a weak theoretical background or on soft data containing large measurement errors can lead to disputable policy messages, in spite of the use of state-of-the-art methodology in its construction."

---

## Validation Checklist (derived from handbook deliverables)

- [ ] Concept defined; sub-groups structured; indicator types specified (input/output/process)
- [ ] Each indicator has a data quality summary (source, coverage, strengths, weaknesses)
- [ ] Missing data pattern assessed; imputation method documented; impact on results tested
- [ ] PCA/FA run; statistical structure compared to theoretical framework; discrepancies discussed
- [ ] Correlation matrix checked; double-counting risk assessed both statistically and conceptually
- [ ] Cronbach's alpha computed for each sub-group
- [ ] Normalisation method selected with reference to data properties; skewness and outliers treated
- [ ] Weighting method selected with justification; within-pillar vs. across-pillar weighting made explicit
- [ ] Aggregation method selected; compensability implications documented
- [ ] Monte Carlo uncertainty analysis run varying: normalisation, weights, aggregation, indicator inclusion/exclusion
- [ ] Uncertainty bounds computed for each unit's rank
- [ ] Sensitivity analysis (Sobol' indices or equivalent) run; dominant uncertainty sources identified
- [ ] Index decomposed at indicator level; path analysis or regression used to assess indicator contributions
- [ ] Composite correlated with external variables; circularity avoided (remove shared indicators before correlating)
- [ ] Correlation robustness tested across alternative weighting schemes
- [ ] Results presented with decomposition and robustness statement
- [ ] All methodological choices documented and explained